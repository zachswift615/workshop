# Workshop Feature Demo - Real Commands in Action
# Run with: vhs feature-demo.tape

Output feature-demo.gif

Set FontSize 16
Set Width 1400
Set Height 900
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 20ms

# Title
Type "# Workshop - Give Claude Code Long-Term Memory"
Enter
Sleep 1s
Enter

# Feature 1: Record a decision
Type "# 1. Record decisions with reasoning"
Enter
Type `workshop decision "Use SQLite for storage" -r "Provides FTS5 full-text search, better performance, and enables complex queries"`
Enter
Sleep 2s

# Feature 2: Record a note
Type "# 2. Track important notes"
Enter
Type `workshop note "Successfully migrated 450+ entries from JSON to SQLite"`
Enter
Sleep 2s

# Feature 3: Search
Type "# 3. Powerful full-text search"
Enter
Type "workshop search SQLite --limit 3"
Enter
Sleep 3s

# Feature 4: The "why" command (killer feature!)
Type "# 4. Ask 'why' - get intelligent answers"
Enter
Type "workshop why SQLite"
Enter
Sleep 4s

# Final
Ctrl+L
Type "# 🚀 Install: pip install claude-workshop"
Sleep 2s
