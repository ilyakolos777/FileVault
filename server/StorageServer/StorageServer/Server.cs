using System.Net;
using System.Net.Sockets;
using StorageServer.Logging;
using StorageServer.Storage;

namespace StorageServer;

public class Server
{
    private readonly int _port;
    private readonly StorageManager _storage;
    private readonly HistoryLogger _logger;
    private TcpListener? _listener;

    public Server(int port, StorageManager storage, HistoryLogger logger)
    {
        _port = port;
        _storage = storage;
        _logger = logger;
    }

    public async Task StartAsync()
    {
        _listener = new TcpListener(IPAddress.Any, _port);
        _listener.Start();
        ConsoleLogger.LogSuccess($"Сервер запущен. Ожидание подключений на порту {_port}...");

        while (true)
        {
            try
            {
                var client = await _listener.AcceptTcpClientAsync();
                var session = new ClientSession(client, _storage, _logger);
                
                // Запускаем сессию в отдельном Task (параллельная обработка клиентов по ТЗ)
                _ = Task.Run(() => session.HandleAsync());
            }
            catch (Exception ex)
            {
                ConsoleLogger.LogError($"Ошибка принятия соединения: {ex.Message}");
            }
        }
    }
}