using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using Xunit;
using StorageServer;
using StorageServer.Logging;
using StorageServer.Storage;

namespace StorageServer.Tests;

public class ClientSessionTests : IDisposable
{
    private readonly string _tempDir;
    private readonly string _logFile;
    private readonly StorageManager _storage;
    private readonly HistoryLogger _logger;

    public ClientSessionTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
        Directory.CreateDirectory(_tempDir);
        _logFile = Path.Combine(_tempDir, "history.log");

        _storage = new StorageManager(_tempDir);
        _logger = new HistoryLogger(_logFile);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, true);
    }

    // Вспомогательный метод для создания пары "Клиент-Сервер" в памяти
    private async Task RunSessionTestAsync(Func<TcpClient, NetworkStream, Task> clientActions)
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;

        // Подключаем тестового клиента
        var clientTask = Task.Run(() => new TcpClient("127.0.0.1", port));
        var serverSideClient = await listener.AcceptTcpClientAsync();
        var client = await clientTask;
        
        var session = new ClientSession(serverSideClient, _storage, _logger);
        
        // ИСПРАВЛЕНИЕ: Обязательно оборачиваем в Task.Run, чтобы сервер ушел в фон и не блокировал тест
        var sessionTask = Task.Run(() => session.HandleAsync()); 

        using (client)
        using (var stream = client.GetStream())
        {
            await clientActions(client, stream);
            
            // Завершаем соединение корректно
            byte[] quitCmd = Encoding.UTF8.GetBytes("QUIT\r\n");
            await stream.WriteAsync(quitCmd);
        }

        await sessionTask; // Дожидаемся завершения
        listener.Stop();
    }

    private async Task SendCommandAsync(NetworkStream stream, string command)
    {
        byte[] buffer = Encoding.UTF8.GetBytes(command + "\r\n");
        await stream.WriteAsync(buffer);
    }

    private async Task<string> ReadTextResponseAsync(NetworkStream stream)
    {
        // Читаем заголовок (до \r\n)
        var ms = new MemoryStream();
        while (true)
        {
            int b = stream.ReadByte();
            if (b == -1) throw new EndOfStreamException();
            ms.WriteByte((byte)b);
            if (b == '\n') break;
        }
        
        string header = Encoding.UTF8.GetString(ms.ToArray()).TrimEnd('\r', '\n');
        var parts = header.Split(' ');
        
        if (parts[0] == "ERR") return header; // Если ошибка, возвращаем заголовок
        
        int length = int.Parse(parts[1]);
        if (length == 0) return "";
        
        byte[] payload = new byte[length];
        int read = 0;
        while (read < length)
        {
            read += await stream.ReadAsync(payload.AsMemory(read, length - read));
        }
        
        return Encoding.UTF8.GetString(payload);
    }

    [Fact]
    public async Task AuthCommand_Success_ReturnsAuthenticated()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            string response = await ReadTextResponseAsync(stream);
            Assert.Equal("Authenticated", response);
        });
    }

    [Fact]
    public async Task PutAndGetFile_Success_TransfersData()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            // 1. Отправляем PUT
            string fileData = "Hello FileVault";
            byte[] dataBytes = Encoding.UTF8.GetBytes(fileData);
            await SendCommandAsync(stream, $"PUT my_file.txt {dataBytes.Length}");
            
            // Отправляем бинарные данные
            await stream.WriteAsync(dataBytes);
            
            string putResp = await ReadTextResponseAsync(stream);
            Assert.Equal("File uploaded successfully", putResp);
            
            // Проверяем, что файл реально создался на диске
            Assert.True(File.Exists(Path.Combine(_tempDir, "my_file.txt")));

            // 2. Скачиваем файл через GET
            await SendCommandAsync(stream, "GET my_file.txt 0");
            string getResp = await ReadTextResponseAsync(stream);
            Assert.Equal(fileData, getResp);
        });
    }

    [Fact]
    public async Task GetFile_FileNotFound_ReturnsError404()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            await SendCommandAsync(stream, "GET missing.txt 0");
            string errorResp = await ReadTextResponseAsync(stream);
            Assert.StartsWith("ERR 404", errorResp);
        });
    }

    [Fact]
    public async Task RenameAndDeleteFile_Success()
    {
        File.WriteAllText(Path.Combine(_tempDir, "old.txt"), "data");

        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            // Переименование
            await SendCommandAsync(stream, "RENAME old.txt new.txt");
            string renResp = await ReadTextResponseAsync(stream);
            Assert.Equal("File renamed", renResp);
            Assert.True(File.Exists(Path.Combine(_tempDir, "new.txt")));

            // Удаление
            await SendCommandAsync(stream, "DELETE new.txt");
            string delResp = await ReadTextResponseAsync(stream);
            Assert.Equal("File deleted", delResp);
            Assert.False(File.Exists(Path.Combine(_tempDir, "new.txt")));
        });
    }

    [Fact]
    public async Task PathTraversalAttack_IsBlocked_ReturnsError403()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            // Пытаемся получить доступ к директории выше
            await SendCommandAsync(stream, "GET ../../../windows/system32/cmd.exe 0");
            string errorResp = await ReadTextResponseAsync(stream);
            
            // Сервер должен перехватить UnauthorizedAccessException и вернуть 403
            Assert.StartsWith("ERR 403", errorResp);
        });
    }

    [Fact]
    public async Task InvalidCommand_ReturnsError400()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            await SendCommandAsync(stream, "UNKNOWN_CMD");
            string errorResp = await ReadTextResponseAsync(stream);
            Assert.StartsWith("ERR 400", errorResp);
        });
    }
    
    [Fact]
    public async Task ListCommand_ReturnsFilesList()
    {
        File.WriteAllText(Path.Combine(_tempDir, "test_file.txt"), "data");

        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            await SendCommandAsync(stream, "LIST");
            string listResp = await ReadTextResponseAsync(stream);
            
            Assert.Contains("test_file.txt", listResp);
        });
    }

    [Fact]
    public async Task HistoryCommand_ReturnsLogData()
    {
        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            await SendCommandAsync(stream, "HISTORY");
            string histResp = await ReadTextResponseAsync(stream);
            
            Assert.Contains("DATE\tUSER\tACTION\tFILE", histResp);
        });
    }

    [Fact]
    public async Task GetFile_WithOffset_ResumesDownload()
    {
        string content = "0123456789";
        File.WriteAllText(Path.Combine(_tempDir, "resume.txt"), content);

        await RunSessionTestAsync(async (client, stream) =>
        {
            await SendCommandAsync(stream, "AUTH Admin");
            await ReadTextResponseAsync(stream);

            // Просим скачать файл, начиная с 5-го байта (проверка логики докачки)
            await SendCommandAsync(stream, "GET resume.txt 5");
            string getResp = await ReadTextResponseAsync(stream);
            
            // Должны получить только вторую половину файла
            Assert.Equal("56789", getResp); 
        });
    }
}