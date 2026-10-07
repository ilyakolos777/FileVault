namespace StorageServer.Storage;

public class DiskChecker
{
    private readonly string _driveRoot;

    public DiskChecker(string storagePath)
    {
        // Извлекаем корень диска (например, "/" на macOS/Linux или "C:\" на Windows)
        _driveRoot = Path.GetPathRoot(Path.GetFullPath(storagePath)) ?? storagePath;
    }

    public bool HasFreeSpace(long bytesRequired)
    {
        try
        {
            var driveInfo = new DriveInfo(_driveRoot);
            return driveInfo.AvailableFreeSpace > bytesRequired;
        }
        catch (Exception)
        {
            // Если ОС не отдает данные о диске (например, проблемы с правами),
            // возвращаем false в целях безопасности.
            return false;
        }
    }
}