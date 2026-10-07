namespace StorageServer.Protocol;

public class ParsedCommand
{
    public string Name { get; set; } = string.Empty;
    public string[] Arguments { get; set; } = Array.Empty<string>();
    
    public bool IsEmpty => string.IsNullOrEmpty(Name);
}

public static class CommandParser
{
    public static ParsedCommand Parse(string commandLine)
    {
        if (string.IsNullOrWhiteSpace(commandLine))
        {
            return new ParsedCommand();
        }

        string[] parts = commandLine.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        
        return new ParsedCommand
        {
            Name = parts[0].ToUpper(), // Нормализуем имя команды к верхнему регистру
            Arguments = parts
        };
    }
}