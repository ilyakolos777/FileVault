using System.Net.Sockets;
using System.Text;
using System.IO;
using System.Collections.Concurrent;
using StorageServer.Logging;
using StorageServer.Protocol;
using StorageServer.Storage;

namespace StorageServer;

public class ClientSession
{
    private static readonly ConcurrentDictionary<string, ClientSession> ActiveUsers = new(StringComparer.OrdinalIgnoreCase);
    // Блокировка файлов: Ключ - имя файла, Значение - флаг занятости
    private static readonly ConcurrentDictionary<string, byte> ActiveFiles = new(StringComparer.OrdinalIgnoreCase);

    private readonly TcpClient _client;
    private readonly StorageManager _storage;
    private readonly HistoryLogger _logger;
    private string _username = "Anonymous";

    public ClientSession(TcpClient client, StorageManager storage, HistoryLogger logger)
    {
        _client = client;
        _storage = storage;
        _logger = logger;
    }

    public async Task HandleAsync()
    {
        string clientEndpoint = _client.Client.RemoteEndPoint?.ToString() ?? "Unknown";
        ConsoleLogger.LogInfo($"Клиент подключен: {clientEndpoint}");

        try
        {
            using var stream = _client.GetStream();
            byte[] ioBuffer = new byte[ProtocolConstants.BufferSize];

            while (_client.Connected)
            {
                string? commandLine = await stream.ReadCommandLineAsync();
                if (commandLine == null) break;

                var command = CommandParser.Parse(commandLine);
                if (command.IsEmpty) continue;

                try
                {
                    await ProcessCommandAsync(command.Name, command.Arguments, stream, ioBuffer);
                }
                catch (Exception ex)
                {
                    await SendErrorAsync(stream, ex);
                }
            }
        }
        catch (Exception ex)
        {
            ConsoleLogger.LogError($"Ошибка соединения с {clientEndpoint}: {ex.Message}");
        }
        finally
        {
            if (_username != "Anonymous") ActiveUsers.TryRemove(_username, out _);
            _client.Close();
            ConsoleLogger.LogInfo($"Клиент отключен: {clientEndpoint} ({_username})");
        }
    }

    // Хелпер для безопасного эксклюзивного доступа к файлу
    private async Task ExecuteWithFileLockAsync(string filename, Func<Task> action)
    {
        if (!ActiveFiles.TryAdd(filename, 1))
            throw new IOException($"Файл '{filename}' занят другой операцией.");
        try
        {
            await action();
        }
        finally
        {
            ActiveFiles.TryRemove(filename, out _);
        }
    }

    private async Task ProcessCommandAsync(string cmdName, string[] args, NetworkStream stream, byte[] buffer)
    {
        switch (cmdName)
        {
            case "AUTH":
                if (args.Length < 2) throw new ArgumentException("Использование: AUTH <username>");
                string reqUser = args[1];
                if (!ActiveUsers.TryAdd(reqUser, this))
                    throw new UnauthorizedAccessException("Пользователь с таким логином уже находится в системе.");
                _username = reqUser;
                await SendTextResponseAsync(stream, "Authenticated");
                break;

            case "LIST":
                string listData = _storage.GetFilesList();
                await SendTextResponseAsync(stream, listData);
                break;

            case "GET":
                if (args.Length < 2) throw new ArgumentException("Использование: GET <filename> [offset]");
                string getFile = args[1];
                long getOffset = args.Length > 2 ? long.Parse(args[2]) : 0;
                await ExecuteWithFileLockAsync(getFile, () => HandleGetAsync(stream, getFile, getOffset, buffer));
                break;

            case "PUT":
                if (args.Length < 3) throw new ArgumentException("Использование: PUT <filename> <size> [offset]");
                string putFile = args[1];
                long size = long.Parse(args[2]);
                long putOffset = args.Length > 3 ? long.Parse(args[3]) : 0;
                await ExecuteWithFileLockAsync(putFile, () => HandlePutAsync(stream, putFile, size, putOffset, buffer));
                break;

            case "DELETE":
                if (args.Length < 2) throw new ArgumentException("Использование: DELETE <filename>");
                string delFile = args[1];
                await ExecuteWithFileLockAsync(delFile, async () => {
                    _storage.DeleteFile(delFile);
                    _logger.LogAction(_username, "DELETE", delFile);
                    await SendTextResponseAsync(stream, "File deleted");
                });
                break;

            case "RENAME":
                if (args.Length < 3) throw new ArgumentException("Использование: RENAME <old_name> <new_name>");
                string oldName = args[1];
                string newName = args[2];
                // Блокируем сразу оба имени, чтобы избежать коллизий
                await ExecuteWithFileLockAsync(oldName, async () => {
                    await ExecuteWithFileLockAsync(newName, async () => {
                        _storage.RenameFile(oldName, newName);
                        _logger.LogAction(_username, "RENAME", $"{oldName} -> {newName}");
                        await SendTextResponseAsync(stream, "File renamed");
                    });
                });
                break;

            case "HISTORY":
                string targetFile = args.Length > 1 ? args[1] : "";
                string history = _logger.GetHistory(targetFile);
                await SendTextResponseAsync(stream, history);
                break;

            case "QUIT":
                _client.Close();
                break;

            default:
                throw new InvalidOperationException($"Неизвестная команда: {cmdName}");
        }
    }

    private async Task HandleGetAsync(NetworkStream stream, string filename, long offset, byte[] buffer)
    {
        using var fs = _storage.OpenRead(filename);
        if (offset >= fs.Length) throw new ArgumentException("Offset превышает размер файла");

        fs.Seek(offset, SeekOrigin.Begin);
        long payloadLength = fs.Length - offset;

        string header = $"{ProtocolConstants.Ok} {payloadLength} {fs.Length}{ProtocolConstants.Terminator}";
        await stream.WriteAsync(Encoding.UTF8.GetBytes(header));

        await fs.CopyToBoundedAsync(stream, payloadLength, buffer);
        _logger.LogAction(_username, offset > 0 ? "DOWNLOAD_RESUME" : "DOWNLOAD", filename);
    }

    private async Task HandlePutAsync(NetworkStream stream, string filename, long size, long offset, byte[] buffer)
    {
        if (!_storage.Disk.HasFreeSpace(size))
            throw new IOException("Недостаточно места на сервере", new Exception(ProtocolConstants.ErrNoSpace));

        if (offset == 0) _storage.BackupIfExists(filename); // Бэкап делаем только при полной перезаписи

        using (var fs = _storage.OpenWrite(filename, offset))
        {
            await stream.CopyToBoundedAsync(fs, size, buffer);
        }

        _logger.LogAction(_username, offset > 0 ? "UPLOAD_RESUME" : "UPLOAD", filename);
        await SendTextResponseAsync(stream, "File uploaded successfully");
    }

    private async Task SendTextResponseAsync(NetworkStream stream, string payload)
    {
        byte[] payloadBytes = Encoding.UTF8.GetBytes(payload);
        string header = $"{ProtocolConstants.Ok} {payloadBytes.Length}{ProtocolConstants.Terminator}";
        await stream.WriteAsync(Encoding.UTF8.GetBytes(header));
        if (payloadBytes.Length > 0) await stream.WriteAsync(payloadBytes);
    }

    private async Task SendErrorAsync(NetworkStream stream, Exception ex)
    {
        string code = ProtocolConstants.ErrInternal;
        if (ex is UnauthorizedAccessException) code = ProtocolConstants.ErrAccessDenied;
        if (ex is FileNotFoundException) code = ProtocolConstants.ErrNotFound;
        if (ex is ArgumentException || ex is InvalidOperationException) code = ProtocolConstants.ErrInvalidArgs;
        if (ex.InnerException?.Message == ProtocolConstants.ErrNoSpace) code = ProtocolConstants.ErrNoSpace;

        string errorMsg = $"{ProtocolConstants.Error} {code} {ex.Message}{ProtocolConstants.Terminator}";
        try { await stream.WriteAsync(Encoding.UTF8.GetBytes(errorMsg)); } catch { }
    }
}