using System.IO;

namespace StorageServer.Storage;

public class StorageManager
{
    private readonly string _rootPath;
    
    // Свойство для доступа к модулю проверки диска
    public DiskChecker Disk { get; }

    public StorageManager(string rootPath)
    {
        _rootPath = Path.GetFullPath(rootPath);
        if (!Directory.Exists(_rootPath))
        {
            Directory.CreateDirectory(_rootPath);
        }
        
        // Инициализируем класс проверки диска
        Disk = new DiskChecker(_rootPath);
    }

    // Критически важно: защита от Path Traversal (../../etc/passwd)
    public string GetSafePath(string filename)
    {
        var targetPath = Path.GetFullPath(Path.Combine(_rootPath, filename));
        if (!targetPath.StartsWith(_rootPath + Path.DirectorySeparatorChar) && targetPath != _rootPath)
        {
            throw new UnauthorizedAccessException("Попытка выхода за пределы корневой директории.");
        }
        return targetPath;
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
                           .Where(f => !f.Name.EndsWith(".bak")) // Бэкапы скрываем из основного списка
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

    public FileStream OpenWrite(string filename)
    {
        var path = GetSafePath(filename);
        return new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
    }

    public void DeleteFile(string filename)
    {
        var path = GetSafePath(filename);
        if (File.Exists(path)) File.Delete(path);
        
        var bakPath = path + ".bak";
        if (File.Exists(bakPath)) File.Delete(bakPath); // Удаляем и бэкап тоже
    }

    public void RenameFile(string oldName, string newName)
    {
        var oldPath = GetSafePath(oldName);
        var newPath = GetSafePath(newName);
        
        if (!File.Exists(oldPath)) throw new FileNotFoundException();
        File.Move(oldPath, newPath, overwrite: false);
    }
}