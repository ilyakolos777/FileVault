namespace StorageServer.Logging;

public class HistoryLogger
{
    private readonly string _logFilePath;
    private readonly object _fileLock = new();

    public HistoryLogger(string logFilePath)
    {
        _logFilePath = logFilePath;
        if (!File.Exists(_logFilePath))
        {
            File.WriteAllText(_logFilePath, "DATE\tUSER\tACTION\tFILE\n");
        }
    }

    public void LogAction(string user, string action, string filename)
    {
        string record = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss}\t{user}\t{action}\t{filename}\n";
        
        lock (_fileLock)
        {
            File.AppendAllText(_logFilePath, record);
        }
    }

    public string GetHistory(string? filterFilename = null)
    {
        lock (_fileLock)
        {
            var lines = File.ReadAllLines(_logFilePath);
            if (string.IsNullOrEmpty(filterFilename)) 
                return string.Join("\n", lines);

            var filtered = lines.Where(l => l.StartsWith("DATE") || l.EndsWith($"\t{filterFilename}") || l.EndsWith($"\t{filterFilename}.bak"));
            return string.Join("\n", filtered);
        }
    }
}