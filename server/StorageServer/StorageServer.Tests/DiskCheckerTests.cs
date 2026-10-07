using System.IO;
using Xunit;
using StorageServer.Storage;

namespace StorageServer.Tests;

public class DiskCheckerTests
{
    [Fact]
    public void HasFreeSpace_SmallFile_ReturnsTrue()
    {
        // Проверяем на временной директории, где точно есть хотя бы 10 байт свободного места
        var checker = new DiskChecker(Path.GetTempPath());
        
        bool hasSpace = checker.HasFreeSpace(10);
        
        Assert.True(hasSpace);
    }

    [Fact]
    public void HasFreeSpace_TooLargeFile_ReturnsFalse()
    {
        var checker = new DiskChecker(Path.GetTempPath());
        
        // Запрашиваем 10 Петабайт — ни на одном диске столько нет
        bool hasSpace = checker.HasFreeSpace(10L * 1024 * 1024 * 1024 * 1024 * 1024);
        
        Assert.False(hasSpace);
    }
}