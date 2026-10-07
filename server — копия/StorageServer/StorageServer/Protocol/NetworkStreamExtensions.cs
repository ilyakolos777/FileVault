using System.Net.Sockets;
using System.Text;

namespace StorageServer.Protocol;

public static class NetworkStreamExtensions
{
    // Читает строго до \r\n, не съедая байты бинарного тела, идущие следом
    public static async Task<string?> ReadCommandLineAsync(this NetworkStream stream, CancellationToken ct = default)
    {
        using var ms = new MemoryStream();
        var delimiter = Encoding.ASCII.GetBytes(ProtocolConstants.Terminator);
        int matched = 0;

        while (true)
        {
            // Побайтовое чтение тут оправдано, так как команды короткие, 
            // а нам критически важно не прочитать лишние бинарные данные в буфер строки.
            int b = stream.ReadByte(); 
            if (b == -1)
            {
                if (ms.Length == 0) return null; // Клиент отключился
                break;
            }

            ms.WriteByte((byte)b);

            if ((byte)b == delimiter[matched])
            {
                matched++;
                if (matched == delimiter.Length)
                {
                    byte[] lineBytes = ms.ToArray();
                    return Encoding.UTF8.GetString(lineBytes, 0, lineBytes.Length - delimiter.Length);
                }
            }
            else
            {
                matched = ((byte)b == delimiter[0]) ? 1 : 0;
            }
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    // Копирует ровно N байт из сокета в файл (защита от недокачки и перекачки)
    public static async Task CopyToBoundedAsync(this Stream source, Stream destination, long bytesToCopy, byte[] buffer, CancellationToken ct = default)
    {
        long remaining = bytesToCopy;
        while (remaining > 0)
        {
            int chunk = (int)Math.Min(buffer.Length, remaining);
            int read = await source.ReadAsync(buffer.AsMemory(0, chunk), ct);
            if (read == 0)
                throw new EndOfStreamException($"Разрыв соединения. Ожидалось еще {remaining} байт.");

            await destination.WriteAsync(buffer.AsMemory(0, read), ct);
            remaining -= read;
        }
    }
}