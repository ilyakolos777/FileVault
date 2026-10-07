namespace StorageServer.Logging;

public static class ConsoleLogger
{
    private static readonly object _lock = new();

    public static void LogInfo(string message) => WriteColor($"[INFO] {DateTime.Now:HH:mm:ss} - {message}", ConsoleColor.Cyan);
    public static void LogSuccess(string message) => WriteColor($"[OK]   {DateTime.Now:HH:mm:ss} - {message}", ConsoleColor.Green);
    public static void LogError(string message) => WriteColor($"[ERR]  {DateTime.Now:HH:mm:ss} - {message}", ConsoleColor.Red);

    private static void WriteColor(string text, ConsoleColor color)
    {
        lock (_lock)
        {
            Console.ForegroundColor = color;
            Console.WriteLine(text);
            Console.ResetColor();
        }
    }
}