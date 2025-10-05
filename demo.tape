# Workshop Demo - Terminal Recording for VHS
# Run with: vhs demo.tape

Output demo.gif

Set FontSize 16
Set Width 1400
Set Height 800
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 20ms

# Title
Type "# Workshop - Persistent Context for Claude Code"
Enter
Sleep 800ms
Type "# Give Claude long-term memory across sessions"
Enter
Enter
Sleep 800ms

# Show workshop command help
Type "workshop --help | head -20"
Enter
Sleep 2s

# Show example decision
Type `echo "✓ Decision recorded: Use SQLite for storage"`
Enter
Type `echo "ℹ Reasoning: Provides FTS5 search and better performance"`
Enter
Sleep 1.5s

# Show example search
Type "# Search all entries"
Enter
Type `echo "Found 3 entries:"`
Enter
Type `echo "  💡 Use SQLite for storage (yesterday)"`
Enter
Sleep 1.5s

# Final
Sleep 500ms
Type "# Install: pip install claude-workshop"
Sleep 2s
