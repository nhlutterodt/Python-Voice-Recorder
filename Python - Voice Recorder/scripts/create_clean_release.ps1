# Voice Recorder Pro - Clean Release Creator
# Creates a production-ready copy of the project for public release
# Author: Neils Haldane-Lutterodt
# Date: August 15, 2025

param(
    [string]$DestinationPath = "d:\voice-recorder-pro-public",
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Verbose
)

# Color functions for better output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Progress { param($Message) Write-Host "🔄 $Message" -ForegroundColor Blue }

# Script configuration
$SourcePath = Split-Path -Parent $PSScriptRoot
$ProjectName = "Voice Recorder Pro"

Write-Host "`n🎤 $ProjectName - Clean Release Creator" -ForegroundColor Magenta
Write-Host "=" * 50 -ForegroundColor Magenta

# Validate source directory
if (-not (Test-Path $SourcePath)) {
    Write-Error "Source directory not found: $SourcePath"
    exit 1
}

# Resolve full path
$SourcePath = Resolve-Path $SourcePath

Write-Info "Source: $SourcePath"
Write-Info "Destination: $DestinationPath"

# Define inclusion and exclusion patterns
$IncludePatterns = @{
    # Core Python application files
    CorePython = @("*.py")
    
    # Configuration files
    Config = @("requirements*.txt", ".gitignore", ".env.template", "*.json", "*.yaml", "*.yml", "*.toml")
    
    # Documentation files
    Documentation = @("README.md", "CONTRIBUTING.md", "LICENSE", "CHANGELOG.md", "*.rst")
    
    # Build and packaging
    Build = @("*.spec", "Dockerfile", "docker-compose*.yml", "Makefile")
    
    # Version control
    VCS = @(".gitignore", ".gitattributes")
}

# Files and patterns to explicitly exclude
$ExcludePatterns = @(
    # Development artifacts (case-insensitive patterns)
    "*ASSESSMENT*", "*SUMMARY*", "*PLAN*", "*CHECKLIST*", "*_SUCCESS*", 
    "*TROUBLESHOOTING*", "*ERROR_LOG*", "*READY_FOR_RELEASE*",
    
    # Personal/temporary files
    "blog_post_draft*", "*.tmp", "*.temp", "build_info.json",
    "launch*.bat", "launch*.ps1", "*.swp", "*.swo", "*~",
    
    # Runtime artifacts
    "recordings/**", "db/**", "*.db", "*.sqlite", "*.sqlite3",
    
    # Cache and build artifacts
    ".pytest_cache/**", ".benchmarks/**", "__pycache__/**", "*.pyc", "*.pyo",
    ".coverage", "htmlcov/**", "build/**", "dist/**", "*.egg-info/**",
    
    # IDE and editor
    ".vscode/**", ".idea/**", "*.swp", "*.swo",
    
    # OS specific
    ".DS_Store", "Thumbs.db", "desktop.ini",
    
    # Git
    ".git/**",
    
    # Documentation archives and development docs
    "docs/archive/**", "docs/assessments/**", "docs/development/**", 
    "docs/changelog/**", "docs/planning/**", "docs/implementation/**", 
    "docs/project/**"
)

# Directory-specific rules
$DirectoryRules = @{
    "cloud" = @{ Include = @("*.py"); Exclude = @("__pycache__/**", "*.pyc") }
    "models" = @{ Include = @("*.py"); Exclude = @("__pycache__/**", "*.pyc") }
    "src" = @{ Include = @("*.py"); Exclude = @("__pycache__/**", "*.pyc") }
    "assets" = @{ Include = @("*"); Exclude = @() }
    "config" = @{ Include = @("*.json", "*.template", "*.yaml", "*.yml"); Exclude = @("client_secrets.json", "*_local.*") }
    "scripts" = @{ Include = @("build_*.py", "*.ps1", "create_*.ps1"); Exclude = @("demo_*.py", "*_test.py", "launch_*.ps1") }
    "tests" = @{ Include = @("test_*.py", "conftest.py", "pytest.ini"); Exclude = @("__pycache__/**", "*.pyc") }
    "docs" = @{ Include = @("*.md", "*.rst", "quickstart/**", "setup/**", "api/**", "images/**"); Exclude = @("archive/**", "assessments/**", "development/**") }
}

function Test-ShouldExclude {
    param($RelativePath, $FileName)
    
    foreach ($pattern in $ExcludePatterns) {
        if ($RelativePath -like $pattern -or $FileName -like $pattern) {
            return $true
        }
    }
    return $false
}

function Test-ShouldInclude {
    param($FilePath, $RelativePath, $FileName)
    
    # Check if explicitly excluded first
    if (Test-ShouldExclude -RelativePath $RelativePath -FileName $FileName) {
        return $false
    }
    
    # Check include patterns
    foreach ($category in $IncludePatterns.Keys) {
        foreach ($pattern in $IncludePatterns[$category]) {
            if ($FileName -like $pattern) {
                return $true
            }
        }
    }
    
    return $false
}

function Get-ProjectStructure {
    Write-Progress "Scanning project structure..."
    
    $structure = @{
        Files = @()
        Directories = @()
        Stats = @{
            TotalFiles = 0
            IncludedFiles = 0
            ExcludedFiles = 0
            TotalDirectories = 0
        }
    }
    
    # Get all files and directories
    $allItems = Get-ChildItem $SourcePath -Recurse -Force | Where-Object { 
        $_.FullName -notlike "*\.git\*" 
    }
    
    foreach ($item in $allItems) {
        $relativePath = $item.FullName.Substring($SourcePath.Length + 1)
        
        if ($item.PSIsContainer) {
            $structure.Directories += @{
                FullPath = $item.FullName
                RelativePath = $relativePath
                Name = $item.Name
            }
            $structure.Stats.TotalDirectories++
        } else {
            $shouldInclude = Test-ShouldInclude -FilePath $item.FullName -RelativePath $relativePath -FileName $item.Name
            
            $fileInfo = @{
                FullPath = $item.FullName
                RelativePath = $relativePath
                Name = $item.Name
                Directory = $item.Directory.Name
                ShouldInclude = $shouldInclude
                Size = $item.Length
            }
            
            $structure.Files += $fileInfo
            $structure.Stats.TotalFiles++
            
            if ($shouldInclude) {
                $structure.Stats.IncludedFiles++
            } else {
                $structure.Stats.ExcludedFiles++
            }
        }
    }
    
    Write-Success "Project scan complete: $($structure.Stats.TotalFiles) files, $($structure.Stats.TotalDirectories) directories"
    Write-Info "  ✅ Including: $($structure.Stats.IncludedFiles) files"
    Write-Info "  ❌ Excluding: $($structure.Stats.ExcludedFiles) files"
    
    return $structure
}

function Copy-ProjectFiles {
    Write-Progress "Creating clean project structure..."
    
    # Create destination directory
    if (Test-Path $DestinationPath) {
        if ($Force) {
            Write-Warning "Removing existing destination directory"
            if (-not $DryRun) {
                Remove-Item $DestinationPath -Recurse -Force
            }
        } else {
            Write-Error "Destination directory already exists. Use -Force to overwrite."
            return $false
        }
    }
    
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
    }
    Write-Success "Created destination directory"
    
    # Get project structure
    $projectStructure = Get-ProjectStructure
    
    # Create necessary directories first
    $neededDirectories = @()
    foreach ($file in $projectStructure.Files | Where-Object { $_.ShouldInclude }) {
        $destPath = Join-Path $DestinationPath $file.RelativePath
        $destDir = Split-Path $destPath -Parent
        
        if ($destDir -and $neededDirectories -notcontains $destDir) {
            $neededDirectories += $destDir
        }
    }
    
    foreach ($dir in $neededDirectories) {
        if ($Verbose) { Write-Info "  📁 Creating directory: $(Split-Path $dir -Leaf)" }
        if (-not $DryRun -and -not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    # Copy files
    $copiedFiles = 0
    $totalSize = 0
    
    foreach ($file in $projectStructure.Files | Where-Object { $_.ShouldInclude }) {
        $destPath = Join-Path $DestinationPath $file.RelativePath
        
        if ($Verbose) { 
            $sizeKB = [math]::Round($file.Size / 1KB, 2)
            Write-Info "  📄 $($file.RelativePath) ($sizeKB KB)" 
        }
        
        if (-not $DryRun) {
            Copy-Item $file.FullPath $destPath -Force
        }
        
        $copiedFiles++
        $totalSize += $file.Size
    }
    
    $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
    Write-Success "Copied $copiedFiles files ($totalSizeMB MB total)"
    
    return $true
}

function New-CleanDocumentation {
    Write-Progress "Creating clean documentation structure..."
    
    $docsPath = Join-Path $DestinationPath "docs"
    
    if (-not $DryRun) {
        # Create essential docs structure
        $docDirs = @("quickstart", "setup", "api", "images")
        foreach ($dir in $docDirs) {
            $dirPath = Join-Path $docsPath $dir
            if (-not (Test-Path $dirPath)) {
                New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
            }
        }
        
        # Create docs README
        $docsReadme = @"
# Voice Recorder Pro Documentation

## Quick Start
- [Installation Guide](setup/installation.md)
- [First Recording](quickstart/first-recording.md)
- [Cloud Setup](setup/cloud-setup.md)

## User Guides
- [Basic Recording](quickstart/basic-recording.md)
- [Audio Editing](quickstart/audio-editing.md)
- [Cloud Integration](quickstart/cloud-features.md)

## Technical Documentation
- [API Reference](api/README.md)
- [Build Instructions](setup/building.md)
- [Contributing](../CONTRIBUTING.md)

## Screenshots
Application screenshots and demos are available in the [images](images/) directory.
"@
        
        Set-Content -Path (Join-Path $docsPath "README.md") -Value $docsReadme
        
        # Create placeholder files for clean structure
        $placeholders = @{
            "quickstart/README.md" = "# Quick Start Guide`n`nGetting started with Voice Recorder Pro..."
            "setup/README.md" = "# Setup and Installation`n`nDetailed setup instructions..."
            "api/README.md" = "# API Documentation`n`nTechnical API reference..."
        }
        
        foreach ($file in $placeholders.Keys) {
            $filePath = Join-Path $docsPath $file
            if (-not (Test-Path $filePath)) {
                Set-Content -Path $filePath -Value $placeholders[$file]
            }
        }
    }
    
    Write-Success "Created clean documentation structure"
}

function New-CleanGitignore {
    Write-Progress "Creating production .gitignore..."
    
    $gitignoreContent = @"
# Voice Recorder Pro - Production .gitignore

# Python
__pycache__/
*.py[cod]
*`$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Application specific
recordings/
db/
*.db
*.sqlite
*.sqlite3

# Build artifacts
build/
dist/
*.spec

# Logs
*.log
logs/

# Configuration (keep templates, exclude actual config)
config/client_secrets.json
config/credentials.json
.env.local

# Development artifacts
.pytest_cache/
.benchmarks/
.coverage
htmlcov/

# Temporary files
*.tmp
*.temp
temp/
tmp/
"@
    
    if (-not $DryRun) {
        Set-Content -Path (Join-Path $DestinationPath ".gitignore") -Value $gitignoreContent
    }
    
    Write-Success "Created production .gitignore"
}

function Show-Summary {
    param($Success, $ProjectStructure)
    
    Write-Host "`n" + ("=" * 50) -ForegroundColor Magenta
    
    if ($Success) {
        Write-Success "Clean release created successfully!"
        Write-Host ""
        Write-Info "📁 Location: $DestinationPath"
        Write-Info "🎯 Ready for: Public GitHub repository"
        
        if ($ProjectStructure) {
            Write-Host ""
            Write-Host "� Project Analysis:" -ForegroundColor Yellow
            Write-Info "  📄 Total files scanned: $($ProjectStructure.Stats.TotalFiles)"
            Write-Info "  ✅ Files included: $($ProjectStructure.Stats.IncludedFiles)"
            Write-Info "  ❌ Files excluded: $($ProjectStructure.Stats.ExcludedFiles)"
            Write-Info "  📁 Directories: $($ProjectStructure.Stats.TotalDirectories)"
            
            # Show file type breakdown
            $fileTypes = $ProjectStructure.Files | Where-Object { $_.ShouldInclude } | 
                Group-Object { [System.IO.Path]::GetExtension($_.Name) } | 
                Sort-Object Count -Descending | 
                Select-Object -First 10
                
            Write-Host ""
            Write-Host "📋 Included File Types:" -ForegroundColor Yellow
            foreach ($type in $fileTypes) {
                $ext = if ($type.Name) { $type.Name } else { "(no extension)" }
                Write-Info "  $ext : $($type.Count) files"
            }
        }
        
        if ($DryRun) {
            Write-Warning "This was a DRY RUN - no files were actually copied"
            Write-Info "Remove -DryRun parameter to perform actual copy"
        } else {
            Write-Host ""
            Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
            Write-Host "  1. Review the cleaned project structure"
            Write-Host "  2. Create new GitHub repository"
            Write-Host "  3. Initialize git and push to new repo:"
            Write-Host "     cd `"$DestinationPath`""
            Write-Host "     git init"
            Write-Host "     git add ."
            Write-Host "     git commit -m `"Initial commit - Voice Recorder Pro v2.0.0-beta`""
            Write-Host "  4. Add screenshots to docs/images/"
            Write-Host "  5. Create first release with executable"
        }
    } else {
        Write-Error "Failed to create clean release"
    }
    
    Write-Host ""
}

# Main execution
try {
    if ($DryRun) {
        Write-Warning "DRY RUN MODE - No files will be copied"
    }
    
    $success = Copy-ProjectFiles
    $projectStructure = $null
    
    if ($success) {
        # Get structure for summary (dry run or actual)
        $projectStructure = Get-ProjectStructure
        New-CleanDocumentation
        New-CleanGitignore
    }
    
    Show-Summary -Success $success -ProjectStructure $projectStructure
    
} catch {
    Write-Error "Script failed: $($_.Exception.Message)"
    if ($Verbose) {
        Write-Error $_.Exception.StackTrace
    }
    exit 1
}
