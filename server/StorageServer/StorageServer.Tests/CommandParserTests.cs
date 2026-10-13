using Xunit;
using StorageServer.Protocol;

namespace StorageServer.Tests;

public class CommandParserTests
{
    [Theory]
    [InlineData("AUTH Admin", "AUTH", 2, "Admin")]
    [InlineData("GET file.txt 100", "GET", 3, "file.txt")]
    [InlineData("  list  ", "LIST", 1, null)]
    public void Parse_ValidCommands_ReturnsCorrectParsedCommand(string? input, string expectedName, int expectedArgsCount, string? expectedArg1)
    {
        // Убрали Warning: передаем пустую строку, если input == null
        var result = CommandParser.Parse(input ?? ""); 
        
        Assert.False(result.IsEmpty);
        Assert.Equal(expectedName, result.Name);
        Assert.Equal(expectedArgsCount, result.Arguments.Length);
        if (expectedArg1 != null) Assert.Equal(expectedArg1, result.Arguments[1]);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(null)]
    public void Parse_EmptyOrNull_ReturnsEmptyCommand(string? input)
    {
        var result = CommandParser.Parse(input ?? ""); 
        Assert.True(result.IsEmpty);
    }
}