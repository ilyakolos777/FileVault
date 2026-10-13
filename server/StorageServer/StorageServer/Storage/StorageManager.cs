using System.IO;

namespace StorageServer.Storage;

public class StorageManager
{
    private readonly string _rootPath;
    public DiskChecker Disk { get; }

    public StorageManager(string rootPath)
    {
        _rootPath = Path.GetFullPath(rootPath);
        if (!Directory.Exists(_rootPath))
        {
            Directory.CreateDirectory(_rootPath);
        }
        Disk = new DiskChecker(_rootPath);
    }

    // Абсолютная защита от Path Traversal (игнорирует любые попытки выйти из папки)
    public string GetSafePath(string filename)
    {
        string safeFileName = Path.GetFileName(filename);
        if (string.IsNullOrWhiteSpace(safeFileName)) throw new ArgumentException("Недопустимое имя файла.");
        return Path.Combine(_rootPath, safeFileName);
    }

    public void BackupIfExists(string filename)
    {
        var targetPath = GetSafePath(filename);
        if (File.Exists(targetPath))
        {
            string bakPath = targetPath + ".bak";
            File.Copy(targetPath, bakPath, overwrite: true);
        }
    }

    public string GetFilesList()
    {
        var dirInfo = new DirectoryInfo(_rootPath);
        var files = dirInfo.GetFiles("*", SearchOption.TopDirectoryOnly)
                           .Where(f => !f.Name.EndsWith(".bak"))
                           .ToList();

        var lines = files.Select(f => 
        {
            bool hasBak = File.Exists(f.FullName + ".bak");
            return $"{f.Name}|{f.Length}|{f.LastWriteTime:yyyy-MM-dd HH:mm:ss}|{(hasBak ? "has_bak" : "no_bak")}";
        });

        return string.Join("\n", lines);
    }

    public FileStream OpenRead(string filename)
    {
        var path = GetSafePath(filename);
        if (!File.Exists(path)) throw new FileNotFoundException();
        return new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
    }

    // Поддержка режима докачки (Append)
    public FileStream OpenWrite(string filename, long offset = 0)
    {
        var path = GetSafePath(filename);
        if (offset > 0)
        {
            if (!File.Exists(path)) throw new FileNotFoundException("Файл для докачки не найден.");
            var fs = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.None);
            fs.Seek(offset, SeekOrigin.Begin);
            return fs;
        }
        return new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
    }

    public void DeleteFile(string filename)
    {
        var path = GetSafePath(filename);
        if (File.Exists(path)) File.Delete(path);
        
        var bakPath = path + ".bak";
        if (File.Exists(bakPath)) File.Delete(bakPath);
    }

    public void RenameFile(string oldName, string newName)
    {
        var oldPath = GetSafePath(oldName);
        var newPath = GetSafePath(newName);
        
        if (!File.Exists(oldPath)) throw new FileNotFoundException();
        File.Move(oldPath, newPath, overwrite: false);
    }
}