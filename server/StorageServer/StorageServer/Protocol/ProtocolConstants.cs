namespace StorageServer.Protocol;

public static class ProtocolConstants
{
    public const int DefaultPort = 5050;
    public const int BufferSize = 64 * 1024; // 64 KB для оптимального сетевого I/O
    public const string Terminator = "\r\n";
    
    public const string Ok = "OK";
    public const string Error = "ERR";
    
    public const string ErrNotFound = "404";
    public const string ErrAccessDenied = "403";
    public const string ErrNoSpace = "507";
    public const string ErrInvalidArgs = "400";
    public const string ErrInternal = "500";
}