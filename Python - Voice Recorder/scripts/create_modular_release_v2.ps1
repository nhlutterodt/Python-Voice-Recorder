# Voice Recorder Pro - Modular Clean Release Creator v2
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

# ================== UTILITY FUNCTIONS ==================

function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Progress { param($Message) Write-Host "🔄 $Message" -ForegroundColor Blue }

# ================== DESTINATION VALIDATION FUNCTIONS ==================

function Test-PathSafety {
    param([string]$Path, [string]$SourcePath)
    
    $issues = @()
    
    # 1. SAFETY: Check for invalid characters (excluding drive letters)
    $pathWithoutDrive = $Path
    if ($Path -match "^[A-Za-z]:") {
        $pathWithoutDrive = $Path.Substring(2)  # Remove drive letter part
    }
    
    $invalidChars = @('<', '>', '"', '|', '?', '*') + [char]0
    foreach ($char in $invalidChars) {
        if ($pathWithoutDrive.Contains($char)) {
            $issues += "Contains invalid character: '$char'"
        }
    }
    
    # 2. SAFETY: Check for reserved Windows names
    $reservedNames = @('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9')
    $pathParts = $Path.Split([System.IO.Path]::DirectorySeparatorChar)
    foreach ($part in $pathParts) {
        if ($part) {  # Skip empty parts
            $nameWithoutExt = [System.IO.Path]::GetFileNameWithoutExtension($part).ToUpper()
            if ($reservedNames -contains $nameWithoutExt) {
                $issues += "Contains reserved Windows name: '$part'"
            }
        }
    }
    
    # 3. SAFETY: Check path length (Windows limit: 260 characters)
    if ($Path.Length -gt 250) {  # Leave some buffer
        $issues += "Path too long: $($Path.Length) characters (Windows limit: 260)"
    }
    
    # 4. SAFETY: Prevent circular reference (destination inside source)
    try {
        $resolvedDest = [System.IO.Path]::GetFullPath($Path)
        $resolvedSource = [System.IO.Path]::GetFullPath($SourcePath)
        
        if ($resolvedDest.StartsWith($resolvedSource, [StringComparison]::OrdinalIgnoreCase)) {
            $issues += "CRITICAL: Destination is inside source directory (would create infinite loop)"
        }
        
        if ($resolvedDest -eq $resolvedSource) {
            $issues += "CRITICAL: Destination cannot be the same as source directory"
        }
    }
    catch {
        $issues += "Cannot resolve path: $($_.Exception.Message)"
    }
    
    # 5. SAFETY: Check for system/critical directories
    $criticalPaths = @(
        $env:SystemRoot,
        $env:ProgramFiles,
        "${env:ProgramFiles(x86)}",
        $env:SystemDrive + '\Windows',
        $env:SystemDrive + '\Program Files',
        $env:SystemDrive + '\Program Files (x86)'
    )
    
    foreach ($criticalPath in $criticalPaths | Where-Object { $_ }) {
        if ($Path.StartsWith($criticalPath, [StringComparison]::OrdinalIgnoreCase)) {
            $issues += "CRITICAL: Cannot write to system directory: $criticalPath"
        }
    }
    
    return @{
        IsValid = ($issues.Count -eq 0)
        Issues = $issues
        HasCriticalIssues = ($issues | Where-Object { $_ -like "CRITICAL:*" }).Count -gt 0
    }
}

function Test-PathPermissions {
    param([string]$Path)
    
    $results = @{
        ParentExists = $false
        ParentWritable = $false
        CanCreate = $false
        HasSpace = $false
        SpaceAvailable = 0
        Issues = @()
    }
    
    try {
        # Get parent directory
        $parentPath = Split-Path $Path -Parent
        if (-not $parentPath) {
            $parentPath = $Path
        }
        
        # Check if parent exists
        if (Test-Path $parentPath) {
            $results.ParentExists = $true
            
            # Test write permissions
            try {
                $testFile = Join-Path $parentPath "temp_write_test_$(Get-Random).tmp"
                "test" | Out-File $testFile -ErrorAction Stop
                Remove-Item $testFile -ErrorAction SilentlyContinue
                $results.ParentWritable = $true
                $results.CanCreate = $true
            }
            catch {
                $results.Issues += "No write permission to parent directory: $parentPath"
            }
            
            # Check disk space (get at least 100MB free space)
            try {
                $drive = Get-WmiObject -Class Win32_LogicalDisk | Where-Object { $parentPath.StartsWith($_.DeviceID) }
                if ($drive) {
                    $results.SpaceAvailable = [math]::Round($drive.FreeSpace / 1MB, 2)
                    $results.HasSpace = $drive.FreeSpace -gt 100MB
                    if (-not $results.HasSpace) {
                        $results.Issues += "Insufficient disk space. Available: $($results.SpaceAvailable)MB, Recommended: >100MB"
                    }
                }
            }
            catch {
                $results.Issues += "Could not check disk space"
            }
        }
        else {
            # Try to create parent directories
            try {
                New-Item -Path $parentPath -ItemType Directory -Force -WhatIf -ErrorAction Stop
                $results.CanCreate = $true
            }
            catch {
                $results.Issues += "Cannot create parent directory: $($_.Exception.Message)"
            }
        }
    }
    catch {
        $results.Issues += "Permission check failed: $($_.Exception.Message)"
    }
    
    return $results
}

function Resolve-DestinationConflict {
    param([string]$Path, [bool]$Force, [bool]$DryRun)
    
    if (-not (Test-Path $Path)) {
        return @{
            Action = "Create"
            FinalPath = $Path
            BackupPath = $null
            Message = "Will create new directory"
        }
    }
    
    # Check if directory is empty
    $items = Get-ChildItem $Path -Force -ErrorAction SilentlyContinue
    if ($items.Count -eq 0) {
        return @{
            Action = "UseEmpty"
            FinalPath = $Path
            BackupPath = $null
            Message = "Directory exists but is empty"
        }
    }
    
    # Directory has contents
    if ($Force) {
        # Create backup with timestamp
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupPath = "$Path-backup-$timestamp"
        
        return @{
            Action = "BackupAndReplace"
            FinalPath = $Path
            BackupPath = $backupPath
            Message = "Will backup existing directory to: $backupPath"
        }
    }
    else {
        # Suggest alternative path with timestamp
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $newPath = "$Path-$timestamp"
        
        return @{
            Action = "SuggestAlternative"
            FinalPath = $newPath
            BackupPath = $null
            Message = "Directory exists with $($items.Count) items. Suggested alternative: $newPath"
        }
    }
}

function New-ValidatedDestination {
    param([string]$Path, [string]$SourcePath, [bool]$Force, [bool]$DryRun)
    
    Write-Progress "🔍 Validating destination path..."
    
    # Step 1: SAFETY - Path validation
    $safetyCheck = Test-PathSafety -Path $Path -SourcePath $SourcePath
    if ($safetyCheck.HasCriticalIssues) {
        Write-Error "CRITICAL SAFETY ISSUES found:"
        foreach ($issue in $safetyCheck.Issues | Where-Object { $_ -like "CRITICAL:*" }) {
            Write-Error "  $issue"
        }
        throw "Destination path failed critical safety validation"
    }
    
    if (-not $safetyCheck.IsValid) {
        Write-Warning "Path validation warnings:"
        foreach ($issue in $safetyCheck.Issues | Where-Object { $_ -notlike "CRITICAL:*" }) {
            Write-Warning "  $issue"
        }
    }
    
    # Step 2: AUTOMATION - Permission and space checks
    $permCheck = Test-PathPermissions -Path $Path
    if ($permCheck.Issues.Count -gt 0) {
        Write-Warning "Permission/space issues:"
        foreach ($issue in $permCheck.Issues) {
            Write-Warning "  $issue"
        }
        
        if (-not $permCheck.CanCreate) {
            throw "Cannot create destination directory due to permission issues"
        }
    }
    
    # Step 3: AUTOMATION - Conflict resolution
    $conflict = Resolve-DestinationConflict -Path $Path -Force $Force -DryRun $DryRun
    
    Write-Info "📁 Destination validation complete"
    Write-Info "  Path: $($conflict.FinalPath)"
    Write-Info "  Action: $($conflict.Action)"
    Write-Info "  Message: $($conflict.Message)"
    
    if ($conflict.BackupPath) {
        Write-Info "  Backup: $($conflict.BackupPath)"
    }
    
    if ($permCheck.HasSpace) {
        Write-Info "  Disk space: $($permCheck.SpaceAvailable)MB available"
    }
    
    # Execute the plan (unless dry run)
    if (-not $DryRun) {
        switch ($conflict.Action) {
            "Create" {
                Write-Progress "Creating destination directory..."
                New-Item -Path $conflict.FinalPath -ItemType Directory -Force | Out-Null
            }
            "UseEmpty" {
                Write-Progress "Using existing empty directory..."
            }
            "BackupAndReplace" {
                Write-Progress "Creating backup of existing directory..."
                Move-Item -Path $Path -Destination $conflict.BackupPath
                New-Item -Path $conflict.FinalPath -ItemType Directory -Force | Out-Null
                Write-Success "Backup created: $($conflict.BackupPath)"
            }
            "SuggestAlternative" {
                Write-Progress "Creating alternative directory..."
                New-Item -Path $conflict.FinalPath -ItemType Directory -Force | Out-Null
            }
        }
    }
    
    return $conflict
}

function Copy-ProjectFiles {
    param($ProjectStructure, $SourcePath, $DestinationPath, $Config, $DryRun)
    
    if ($DryRun) {
        Write-Info "DRY RUN: Would copy $($ProjectStructure.Stats.IncludedFiles) files"
        return
    }
    
    Write-Progress "📁 Copying project files to destination..."
    
    $filesToCopy = $ProjectStructure.Files | Where-Object { $_.ShouldInclude }
    $copiedCount = 0
    $errorCount = 0
    $errors = @()
    
    foreach ($file in $filesToCopy) {
        try {
            # Calculate destination path
            $relativePath = $file.RelativePath
            $destFilePath = Join-Path $DestinationPath $relativePath
            $destDir = Split-Path $destFilePath -Parent
            
            # Create destination directory if it doesn't exist
            if (-not (Test-Path $destDir)) {
                New-Item -Path $destDir -ItemType Directory -Force | Out-Null
            }
            
            # Copy the file
            Copy-Item -Path $file.FullPath -Destination $destFilePath -Force
            $copiedCount++
            
            if ($copiedCount % 10 -eq 0) {
                Write-Progress "📄 Copied $copiedCount/$($filesToCopy.Count) files..."
            }
        }
        catch {
            $errorCount++
            $errors += "Failed to copy $($file.RelativePath): $($_.Exception.Message)"
            Write-Warning "Failed to copy: $($file.RelativePath)"
        }
    }
    
    Write-Success "File copying complete!"
    Write-Info "  ✅ Successfully copied: $copiedCount files"
    
    if ($errorCount -gt 0) {
        Write-Warning "  ⚠️ Errors encountered: $errorCount files"
        if ($errors.Count -gt 0) {
            Write-Host ""
            Write-Host "❌ Copy Errors:" -ForegroundColor Red
            foreach ($errorMsg in $errors | Select-Object -First 5) {
                Write-Warning "  $errorMsg"
            }
            if ($errors.Count -gt 5) {
                Write-Warning "  ... and $($errors.Count - 5) more errors"
            }
        }
    }
    
    return @{
        CopiedFiles = $copiedCount
        Errors = $errorCount
        ErrorDetails = $errors
    }
}

function Write-ReleaseSummary {
    param($ProjectStructure, $DestinationPath, $Config, $CopyResult, $ValidationResult)
    
    Write-Host ""
    Write-Host "🎉 RELEASE CREATION COMPLETE!" -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    
    Write-Host ""
    Write-Info "📦 Release Details:"
    Write-Info "  Project: $($Config.ProjectInfo.Name) v$($Config.ProjectInfo.Version)"
    Write-Info "  Type: $($Config.ProjectInfo.ReleaseType)"
    Write-Info "  Location: $DestinationPath"
    
    Write-Host ""
    Write-Info "📊 File Statistics:"
    Write-Info "  Total files processed: $($ProjectStructure.Stats.TotalFiles)"
    Write-Info "  Files included: $($ProjectStructure.Stats.IncludedFiles)"
    Write-Info "  Files excluded: $($ProjectStructure.Stats.ExcludedFiles)"
    Write-Info "  Successfully copied: $($CopyResult.CopiedFiles)"
    
    if ($CopyResult.Errors -gt 0) {
        Write-Info "  Copy errors: $($CopyResult.Errors)"
    }
    
    # Calculate efficiency
    $efficiency = [math]::Round(($ProjectStructure.Stats.IncludedFiles / $ProjectStructure.Stats.TotalFiles) * 100, 1)
    Write-Info "  Filtering efficiency: $efficiency%"
    
    if ($ValidationResult.BackupPath) {
        Write-Host ""
        Write-Info "💾 Backup Information:"
        Write-Info "  Previous content backed up to: $($ValidationResult.BackupPath)"
    }
    
    Write-Host ""
    Write-Host "🔗 Quick Actions:" -ForegroundColor Yellow
    Write-Host "  📁 Open destination: explorer `"$DestinationPath`""
    Write-Host "  📋 View README: Get-Content `"$DestinationPath\README.md`""
    Write-Host "  🚀 Run application: cd `"$DestinationPath`" && python enhanced_main.py"
    
    Write-Host ""
    Write-Success "Release successfully created with enterprise-grade safety validation!"
}

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
            Write-Host "   Usage: -ConfigFile `"scripts\$($file.Name)`""
        }
        catch {
            Write-Warning "   Invalid XML configuration: $($file.Name)"
        }
    }
    Write-Host ""
}

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
        if ($xmlConfig.ReleaseConfiguration.IncludePatterns.Category) {
            foreach ($category in $xmlConfig.ReleaseConfiguration.IncludePatterns.Category) {
                $patterns = @()
                if ($category.Pattern) {
                    foreach ($pattern in $category.Pattern) {
                        $patterns += $pattern
                    }
                }
                $config.IncludePatterns[$category.name] = $patterns
            }
        }
        
        # Parse exclude patterns
        if ($xmlConfig.ReleaseConfiguration.ExcludePatterns.Category) {
            foreach ($category in $xmlConfig.ReleaseConfiguration.ExcludePatterns.Category) {
                if ($category.Pattern) {
                    foreach ($pattern in $category.Pattern) {
                        $config.ExcludePatterns += $pattern
                    }
                }
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
    param($Config, $SourcePath)
    
    Write-Progress "Scanning project structure with XML configuration..."
    
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

# ================== MAIN SCRIPT ==================

# Script initialization
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

# Main execution
try {
    if ($DryRun) {
        Write-Warning "DRY RUN MODE - No files will be copied"
    }
    
    # SAFETY FIRST: Validate destination path
    Write-Host ""
    Write-Host "🔒 Safety & Validation Checks" -ForegroundColor Yellow
    Write-Host "=" * 40 -ForegroundColor Yellow
    
    $destinationResult = New-ValidatedDestination -Path $DestinationPath -SourcePath $SourcePath -Force $Force -DryRun $DryRun
    $validatedDestination = $destinationResult.FinalPath
    
    Write-Host ""
    Write-Host "📊 Project Analysis" -ForegroundColor Yellow
    Write-Host "=" * 40 -ForegroundColor Yellow
    
    # Get project structure
    $projectStructure = Get-ProjectStructure -Config $config -SourcePath $SourcePath
    
    # Copy files to destination
    Write-Host ""
    Write-Host "📁 File Operations" -ForegroundColor Yellow
    Write-Host "=" * 40 -ForegroundColor Yellow
    
    $copyResult = Copy-ProjectFiles -ProjectStructure $projectStructure -SourcePath $SourcePath -DestinationPath $validatedDestination -Config $config -DryRun $DryRun
    
    # Show comprehensive results
    Write-ReleaseSummary -ProjectStructure $projectStructure -DestinationPath $validatedDestination -Config $config -CopyResult $copyResult -ValidationResult $destinationResult
    
} catch {
    Write-Error "Script failed: $($_.Exception.Message)"
    if ($Verbose) {
        Write-Error $_.Exception.StackTrace
    }
    exit 1
}
