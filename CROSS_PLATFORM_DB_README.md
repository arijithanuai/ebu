# Cross-Platform Microsoft Access Database Support

## Problem
The original code was using `pyodbc` with the Microsoft Access Driver, which only works on Windows systems. When running on Linux, this caused the error:
```
Database error: ('01000', "[01000] [unixODBC][Driver Manager]Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)' : file not found (0) (SQLDriverConnect)")
```

## Solution
Implemented a cross-platform solution that automatically detects the operating system and uses the appropriate method:

### Windows (os.name == 'nt')
- Uses `pyodbc` with Microsoft Access Driver
- Original functionality preserved

### Linux/Unix (os.name != 'nt')
- Uses **MDBTools** (mdbtools package)
- Command-line tools: `mdb-tables`, `mdb-export`, `mdb-sql`

## Installation Requirements

### Linux/Unix Systems
```bash
# Install MDBTools system package
sudo apt-get install mdbtools

# Install Python package (in virtual environment)
pip install mdbtools==0.3.14
```

### Windows Systems
```bash
# Install pyodbc (already in requirements)
pip install pyodbc==5.2.0
```

## How It Works

### Platform Detection
The code automatically detects the operating system:
```python
if os.name == 'nt':  # Windows
    # Use pyodbc
else:  # Linux/Unix
    # Use MDBTools
```

### Database Operations

#### Windows (pyodbc)
```python
import pyodbc
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ={db_path};'
conn = pyodbc.connect(conn_str)
df = pd.read_sql_query("SELECT * FROM [TableName]", conn)
```

#### Linux (MDBTools)
```python
import subprocess

# Get table names
result = subprocess.run(['mdb-tables', '-1', db_path], 
                       capture_output=True, text=True, check=True)

# Export table data
result = subprocess.run(['mdb-export', db_path, table_name], 
                       capture_output=True, text=True, check=True)
df = pd.read_csv(io.StringIO(result.stdout))
```

## Files Modified

1. **`ebu/Scripts/main.py`** - Main validation script with cross-platform support
2. **`ebu/Scripts/requirements.txt`** - Added mdbtools dependency
3. **`requirements.txt`** - Added mdbtools and pyodbc dependencies
4. **`test_mdbtools.py`** - Test script to verify installation

## Testing

Run the test script to verify MDBTools installation:
```bash
source myevn/bin/activate
python test_mdbtools.py
```

## Benefits

1. **Cross-platform compatibility** - Works on both Windows and Linux
2. **No code changes needed** - Automatic platform detection
3. **Backward compatibility** - Windows functionality unchanged
4. **Open source solution** - MDBTools is free and well-maintained

## Troubleshooting

### Linux Issues
- **MDBTools not found**: Install with `sudo apt-get install mdbtools`
- **Permission denied**: Ensure proper file permissions on .accdb files
- **Import errors**: Install Python package with `pip install mdbtools==0.3.14`

### Windows Issues
- **pyodbc error**: Ensure Microsoft Access Database Engine is installed
- **Driver not found**: Install Microsoft Access Database Engine 2016 or later

## Notes

- MDBTools provides read-only access to Access databases
- For write operations, consider using a different approach
- The solution maintains the same API for both platforms
- All existing validation logic remains unchanged
