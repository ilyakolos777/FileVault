using System;
using System.IO;
using Xunit;
using StorageServer.Logging;

namespace StorageServer.Tests;

public class HistoryLoggerTests : IDisposable
{
    private readonly string _logFile;
    private readonly HistoryLogger _logger;

    public HistoryLoggerTests()
    {
        // Генерируем уникальное имя файла в Temp, но НЕ создаем сам файл
        _logFile = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString() + ".log");
        _logger = new HistoryLogger(_logFile);
    }

    public void Dispose()
    {
        if (File.Exists(_logFile)) File.Delete(_logFile);
    }

    [Fact]
    public void Constructor_CreatesFileWithHeader()
    {
        string[] lines = File.ReadAllLines(_logFile);
        Assert.Equal("DATE\tUSER\tACTION\tFILE", lines[0]);
    }

    [Fact]
    public void LogAction_AppendsCorrectly()
    {
        _logger.LogAction("Admin", "UPLOAD", "file.txt");
        string[] lines = File.ReadAllLines(_logFile);
        
        Assert.Equal(2, lines.Length);
        Assert.Contains("\tAdmin\tUPLOAD\tfile.txt", lines[1]);
    }

    [Fact]
    public void GetHistory_WithFilter_ReturnsOnlyMatchingLines()
    {
        _logger.LogAction("Admin", "UPLOAD", "file1.txt");
        _logger.LogAction("Admin", "DELETE", "file2.txt");
        
        string history = _logger.GetHistory("file1.txt");
        
        Assert.Contains("file1.txt", history);
        Assert.DoesNotContain("file2.txt", history);
    }
    
    [Fact]
    public void GetHistory_WithoutFilter_ReturnsAllLines()
    {
        _logger.LogAction("Admin", "UPLOAD", "file1.txt");
        string history = _logger.GetHistory();
        Assert.Contains("file1.txt", history);
        Assert.Contains("DATE\tUSER", history);
    }
}