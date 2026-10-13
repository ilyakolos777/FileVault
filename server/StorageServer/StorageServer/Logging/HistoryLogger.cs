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
        // Защита от TSV-инъекций
        string safeUser = user.Replace("\t", " ").Replace("\n", " ").Replace("\r", " ");
        string safeAction = action.Replace("\t", " ").Replace("\n", " ").Replace("\r", " ");
        string safeFilename = filename.Replace("\t", " ").Replace("\n", " ").Replace("\r", " ");

        string record = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss}\t{safeUser}\t{safeAction}\t{safeFilename}\n";
        
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

            // Безопасный поиск с учетом санитаризованных имен
            string safeFilter = filterFilename.Replace("\t", " ").Replace("\n", " ").Replace("\r", " ");
            var filtered = lines.Where(l => l.StartsWith("DATE") || l.EndsWith($"\t{safeFilter}") || l.EndsWith($"\t{safeFilter}.bak"));
            return string.Join("\n", filtered);
        }
    }
}