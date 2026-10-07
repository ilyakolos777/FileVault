using StorageServer;
using StorageServer.Logging;
using StorageServer.Protocol;
using StorageServer.Storage;

class Program
{
    static async Task Main(string[] args)
    {
        Console.Title = "FileVault Server";
        
        // Настраиваем пути относительно места запуска сервера (например, папка FileVault/storage_data)
        string baseDir = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
        string storageDir = Path.Combine(baseDir, "storage_data", "files");
        string logFile = Path.Combine(baseDir, "storage_data", "history.log");

        try
        {
            // Убеждаемся, что каталоги существуют
            Directory.CreateDirectory(storageDir);
            Directory.CreateDirectory(Path.GetDirectoryName(logFile)!);

            var storage = new StorageManager(storageDir);
            var logger = new HistoryLogger(logFile);
            
            ConsoleLogger.LogInfo("Инициализация...");
            ConsoleLogger.LogInfo($"Директория хранения: {storageDir}");
            ConsoleLogger.LogInfo($"Журнал операций: {logFile}");

            var server = new Server(ProtocolConstants.DefaultPort, storage, logger);
            await server.StartAsync();
        }
        catch (Exception ex)
        {
            ConsoleLogger.LogError($"Критическая ошибка запуска: {ex.Message}");
        }
    }
}