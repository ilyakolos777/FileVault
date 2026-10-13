using System;
using System.IO;
using System.Linq;
using Xunit;
using StorageServer.Storage;

namespace StorageServer.Tests;

public class StorageManagerTests : IDisposable
{
    private readonly string _tempDir;
    private readonly StorageManager _storage;

    public StorageManagerTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
        Directory.CreateDirectory(_tempDir);
        _storage = new StorageManager(_tempDir);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, true);
    }

    [Fact]
    public void GetSafePath_ValidFile_ReturnsCorrectPath()
    {
        string expected = Path.Combine(_tempDir, "report.txt");
        string actual = _storage.GetSafePath("report.txt");
        Assert.Equal(expected, actual);
    }

    [Fact]
    public void GetSafePath_PathTraversalAttempt_ReturnsOnlyFilename()
    {
        // Теперь метод игнорирует вредоносный путь и безопасно извлекает только имя файла
        string expected = Path.Combine(_tempDir, "cmd.exe");
        string actual = _storage.GetSafePath("../../../windows/system32/cmd.exe");
        Assert.Equal(expected, actual);
    }

    [Fact]
    public void BackupIfExists_FileExists_CreatesBakFile()
    {
        string filename = "data.txt";
        File.WriteAllText(Path.Combine(_tempDir, filename), "test content");
        
        _storage.BackupIfExists(filename);
        
        Assert.True(File.Exists(Path.Combine(_tempDir, filename + ".bak")));
    }

    [Fact]
    public void GetFilesList_IgnoresBakFiles_AndFormatsOutputCorrectly()
    {
        File.WriteAllText(Path.Combine(_tempDir, "file1.txt"), "123");
        File.WriteAllText(Path.Combine(_tempDir, "file1.txt.bak"), "old");
        File.WriteAllText(Path.Combine(_tempDir, "file2.txt"), "12345");
    
        string result = _storage.GetFilesList();
        string[] lines = result.Split('\n').OrderBy(l => l).ToArray();
    
        Assert.Equal(2, lines.Length);
        Assert.Contains("file1.txt|3|", lines[0]);
        Assert.Contains("|has_bak", lines[0]);
        Assert.Contains("file2.txt|5|", lines[1]);
        Assert.Contains("|no_bak", lines[1]);
    }

    [Fact]
    public void DeleteFile_RemovesMainFile_And_BakFile()
    {
        string filename = "delete_me.txt";
        File.WriteAllText(Path.Combine(_tempDir, filename), "data");
        File.WriteAllText(Path.Combine(_tempDir, filename + ".bak"), "data");
        
        _storage.DeleteFile(filename);
        
        Assert.False(File.Exists(Path.Combine(_tempDir, filename)));
        Assert.False(File.Exists(Path.Combine(_tempDir, filename + ".bak")));
    }

    [Fact]
    public void RenameFile_ValidNames_MovesFile()
    {
        string oldName = "old.txt";
        string newName = "new.txt";
        File.WriteAllText(Path.Combine(_tempDir, oldName), "content");
        
        _storage.RenameFile(oldName, newName);
        
        Assert.False(File.Exists(Path.Combine(_tempDir, oldName)));
        Assert.True(File.Exists(Path.Combine(_tempDir, newName)));
    }
    
    [Fact]
    public void OpenRead_NonExistentFile_ThrowsFileNotFoundException()
    {
        Assert.Throws<FileNotFoundException>(() => _storage.OpenRead("missing.txt"));
    }
}