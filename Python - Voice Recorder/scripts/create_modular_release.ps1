# Voice Recorder Pro - Modular Clean Release Creator
# Configurable release generator using XML configuration files
# Author: Neils Haldane-Lutterodt
# Date: August 15, 2025

param(
    [string]$DestinationPath = "d:\voice-recorder-pro-release",
    [string]$ConfigFile = "scripts\release-config-public.xml",
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Verbose,
    [switch]$ListConfigs
)

# Color functions for better output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Progress { param($Message) Write-Host "🔄 $Message" -ForegroundColor Blue }

function Show-AvailableConfigs {
    param($SourcePath)
    
    Write-Host "`n📋 Available Release Configurations:" -ForegroundColor Yellow
    
    $configFiles = Get-ChildItem (Join-Path $SourcePath "scripts") -Filter "release-config-*.xml"
    
    if ($configFiles.Count -eq 0) {
        Write-Warning "No configuration files found in scripts/ directory"
        return
    }
    
    foreach ($file in $configFiles) {
        try {
            [xml]$xmlConfig = Get-Content $file.FullName
            $projectInfo = $xmlConfig.ReleaseConfiguration.ProjectInfo
            
            Write-Host ""
            Write-Info "📄 $($file.Name)"
            Write-Host "   Name: $($projectInfo.Name)"
            Write-Host "   Type: $($projectInfo.ReleaseType)"
            Write-Host "   Description: $($projectInfo.Description)"
            Write-Host "   Usage: -ConfigFile `"$($file.Name)`""
        }
        catch {
            Write-Warning "   Invalid XML configuration: $($file.Name)"
        }
    }
    Write-Host ""
}

# Script configuration
$SourcePath = Split-Path -Parent $PSScriptRoot

Write-Host "`n🎤 Voice Recorder Pro - Modular Release Creator" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

# Validate source directory
if (-not (Test-Path $SourcePath)) {
    Write-Error "Source directory not found: $SourcePath"
    exit 1
}

# Resolve full path
$SourcePath = Resolve-Path $SourcePath

# Handle special commands
if ($ListConfigs) {
    Show-AvailableConfigs -SourcePath $SourcePath
    exit 0
}

# Load and validate configuration
$config = Import-ReleaseConfiguration -ConfigPath $ConfigFile -SourcePath $SourcePath

if (-not $config) {
    Write-Error "Failed to load configuration from: $ConfigFile"
    exit 1
}

Write-Info "Configuration: $($config.ProjectInfo.Name) v$($config.ProjectInfo.Version) ($($config.ProjectInfo.ReleaseType))"
Write-Info "Source: $SourcePath"
Write-Info "Destination: $DestinationPath"

function Import-ReleaseConfiguration {
    param([string]$ConfigPath, [string]$SourcePath)
    
    $fullConfigPath = if ([System.IO.Path]::IsPathRooted($ConfigPath)) {
        $ConfigPath
    } else {
        Join-Path $SourcePath $ConfigPath
    }
    
    if (-not (Test-Path $fullConfigPath)) {
        Write-Error "Configuration file not found: $fullConfigPath"
        return $null
    }
    
    try {
        Write-Progress "Loading configuration from: $(Split-Path $fullConfigPath -Leaf)"
        [xml]$xmlConfig = Get-Content $fullConfigPath
        
        # Parse the XML into a PowerShell object
        $config = @{
            ProjectInfo = @{
                Name = $xmlConfig.ReleaseConfiguration.ProjectInfo.Name
                Version = $xmlConfig.ReleaseConfiguration.ProjectInfo.Version
                Description = $xmlConfig.ReleaseConfiguration.ProjectInfo.Description
                ReleaseType = $xmlConfig.ReleaseConfiguration.ProjectInfo.ReleaseType
            }
            IncludePatterns = @{}
            ExcludePatterns = @()
            DirectoryRules = @{}
            PostProcessing = @{
                CreateCleanGitignore = [bool]::Parse($xmlConfig.ReleaseConfiguration.PostProcessing.CreateCleanGitignore)
                CreateDocumentationStructure = [bool]::Parse($xmlConfig.ReleaseConfiguration.PostProcessing.CreateDocumentationStructure)
                ValidateEssentialFiles = [bool]::Parse($xmlConfig.ReleaseConfiguration.PostProcessing.ValidateEssentialFiles)
            }
            EssentialFiles = @()
        }
        
        # Parse include patterns
        foreach ($category in $xmlConfig.ReleaseConfiguration.IncludePatterns.Category) {
            $patterns = @()
            foreach ($pattern in $category.Pattern) {
                $patterns += $pattern
            }
            $config.IncludePatterns[$category.name] = $patterns
        }
        
        # Parse exclude patterns
        foreach ($category in $xmlConfig.ReleaseConfiguration.ExcludePatterns.Category) {
            foreach ($pattern in $category.Pattern) {
                $config.ExcludePatterns += $pattern
            }
        }
        
        # Parse directory rules
        if ($xmlConfig.ReleaseConfiguration.DirectoryRules.Directory) {
            foreach ($directory in $xmlConfig.ReleaseConfiguration.DirectoryRules.Directory) {
                $includePatterns = @()
                $excludePatterns = @()
                
                if ($directory.Include.Pattern) {
                    foreach ($pattern in $directory.Include.Pattern) {
                        $includePatterns += $pattern
                    }
                }
                
                if ($directory.Exclude.Pattern) {
                    foreach ($pattern in $directory.Exclude.Pattern) {
                        $excludePatterns += $pattern
                    }
                }
                
                $config.DirectoryRules[$directory.name] = @{
                    Include = $includePatterns
                    Exclude = $excludePatterns
                    Description = $directory.description
                }
            }
        }
        
        # Parse essential files
        if ($xmlConfig.ReleaseConfiguration.EssentialFiles.File) {
            foreach ($file in $xmlConfig.ReleaseConfiguration.EssentialFiles.File) {
                $config.EssentialFiles += $file
            }
        }
        
        Write-Success "Configuration loaded successfully"
        
        if ($Verbose) {
            Write-Host ""
            Write-Host "📊 Configuration Summary:" -ForegroundColor Yellow
            Write-Info "  Include Categories: $($config.IncludePatterns.Keys.Count)"
            Write-Info "  Exclude Patterns: $($config.ExcludePatterns.Count)"
            Write-Info "  Directory Rules: $($config.DirectoryRules.Keys.Count)"
            Write-Info "  Essential Files: $($config.EssentialFiles.Count)"
        }
        
        return $config
    }
    catch {
        Write-Error "Failed to parse configuration file: $($_.Exception.Message)"
        return $null
    }
}

function Test-ShouldExclude {
    param($RelativePath, $FileName, $Config)
    
    foreach ($pattern in $Config.ExcludePatterns) {
        if ($RelativePath -like $pattern -or $FileName -like $pattern) {
            return $true
        }
    }
    return $false
}

function Test-ShouldInclude {
    param($FilePath, $RelativePath, $FileName, $Config)
    
    # Check if explicitly excluded first
    if (Test-ShouldExclude -RelativePath $RelativePath -FileName $FileName -Config $Config) {
        return $false
    }
    
    # Check directory-specific rules first
    $directory = Split-Path $RelativePath -Parent
    if ($directory) {
        $dirName = Split-Path $directory -Leaf
        if ($Config.DirectoryRules.ContainsKey($dirName)) {
            $dirRule = $Config.DirectoryRules[$dirName]
            
            # Check directory exclude patterns
            foreach ($pattern in $dirRule.Exclude) {
                if ($RelativePath -like "*$pattern*" -or $FileName -like $pattern) {
                    return $false
                }
            }
            
            # Check directory include patterns
            foreach ($pattern in $dirRule.Include) {
                if ($FileName -like $pattern -or $RelativePath -like "*$pattern*") {
                    return $true
                }
            }
        }
    }
    
    # Check global include patterns
    foreach ($category in $Config.IncludePatterns.Keys) {
        foreach ($pattern in $Config.IncludePatterns[$category]) {
            if ($FileName -like $pattern) {
                return $true
            }
        }
    }
    
    return $false
}

function Get-ProjectStructure {
    param($Config)
    
    Write-Progress "Scanning project structure with configuration..."
    
    $structure = @{
        Files = @()
        Directories = @()
        Stats = @{
            TotalFiles = 0
            IncludedFiles = 0
            ExcludedFiles = 0
            TotalDirectories = 0
        }
        ConfigSummary = @{
            IncludeCategories = $Config.IncludePatterns.Keys.Count
            ExcludePatterns = $Config.ExcludePatterns.Count
            DirectoryRules = $Config.DirectoryRules.Keys.Count
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
            $shouldInclude = Test-ShouldInclude -FilePath $item.FullName -RelativePath $relativePath -FileName $item.Name -Config $Config
            
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

function Test-EssentialFiles {
    param($ProjectStructure, $Config)
    
    if (-not $Config.PostProcessing.ValidateEssentialFiles) {
        return $true
    }
    
    Write-Progress "Validating essential files..."
    
    $missingFiles = @()
    $includedFiles = $ProjectStructure.Files | Where-Object { $_.ShouldInclude } | ForEach-Object { $_.RelativePath }
    
    foreach ($essentialFile in $Config.EssentialFiles) {
        if ($includedFiles -notcontains $essentialFile) {
            $missingFiles += $essentialFile
        }
    }
    
    if ($missingFiles.Count -gt 0) {
        Write-Warning "Missing essential files:"
        foreach ($file in $missingFiles) {
            Write-Warning "  ❌ $file"
        }
        return $false
    }
    
    Write-Success "All essential files present"
    return $true
}

function Copy-ProjectFiles {
    param($Config)
    
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
    $projectStructure = Get-ProjectStructure -Config $Config
    
    # Validate essential files
    if (-not (Test-EssentialFiles -ProjectStructure $projectStructure -Config $Config)) {
        Write-Error "Essential files validation failed"
        return $false
    }
    
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
    
    return @{
        Success = $true
        ProjectStructure = $projectStructure
    }
}

function New-CleanGitignore {
    param($Config)
    
    if (-not $Config.PostProcessing.CreateCleanGitignore) {
        return
    }
    
    Write-Progress "Creating production .gitignore..."
    
    $gitignoreContent = @"
# $($Config.ProjectInfo.Name) - Production .gitignore
# Generated by Modular Release Creator

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

function New-CleanDocumentation {
    param($Config)
    
    if (-not $Config.PostProcessing.CreateDocumentationStructure) {
        return
    }
    
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
# $($Config.ProjectInfo.Name) Documentation

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

---
*Documentation structure generated for $($Config.ProjectInfo.ReleaseType) release*
"@
        
        Set-Content -Path (Join-Path $docsPath "README.md") -Value $docsReadme
        
        # Create placeholder files for clean structure
        $placeholders = @{
            "quickstart/README.md" = "# Quick Start Guide`n`nGetting started with $($Config.ProjectInfo.Name)..."
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

function Show-Summary {
    param($Result, $Config)
    
    Write-Host "`n" + ("=" * 60) -ForegroundColor Magenta
    
    if ($Result.Success) {
        Write-Success "Clean release created successfully!"
        Write-Host ""
        Write-Info "📁 Location: $DestinationPath"
        Write-Info "🎯 Release Type: $($Config.ProjectInfo.ReleaseType)"
        Write-Info "📦 Project: $($Config.ProjectInfo.Name) v$($Config.ProjectInfo.Version)"
        
        if ($Result.ProjectStructure) {
            Write-Host ""
            Write-Host "📊 Release Analysis:" -ForegroundColor Yellow
            Write-Info "  📄 Total files scanned: $($Result.ProjectStructure.Stats.TotalFiles)"
            Write-Info "  ✅ Files included: $($Result.ProjectStructure.Stats.IncludedFiles)"
            Write-Info "  ❌ Files excluded: $($Result.ProjectStructure.Stats.ExcludedFiles)"
            Write-Info "  📁 Directories: $($Result.ProjectStructure.Stats.TotalDirectories)"
            
            # Show configuration summary
            Write-Host ""
            Write-Host "⚙️ Configuration Used:" -ForegroundColor Yellow
            Write-Info "  📋 Include Categories: $($Result.ProjectStructure.ConfigSummary.IncludeCategories)"
            Write-Info "  🚫 Exclude Patterns: $($Result.ProjectStructure.ConfigSummary.ExcludePatterns)"
            Write-Info "  📁 Directory Rules: $($Result.ProjectStructure.ConfigSummary.DirectoryRules)"
            
            # Show file type breakdown
            $fileTypes = $Result.ProjectStructure.Files | Where-Object { $_.ShouldInclude } | 
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
            Write-Host "     git commit -m `"Initial commit - $($Config.ProjectInfo.Name) v$($Config.ProjectInfo.Version) ($($Config.ProjectInfo.ReleaseType) Release)`""
            Write-Host "  4. Add screenshots to docs/images/ (if applicable)"
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
    
    $result = Copy-ProjectFiles -Config $config
    
    if ($result.Success) {
        New-CleanDocumentation -Config $config
        New-CleanGitignore -Config $config
    }
    
    Show-Summary -Result $result -Config $config
    
} catch {
    Write-Error "Script failed: $($_.Exception.Message)"
    if ($Verbose) {
        Write-Error $_.Exception.StackTrace
    }
    exit 1
}
