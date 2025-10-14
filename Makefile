SHELL := powershell.exe

.PHONY: setup install-dev unit import test

setup:
	@powershell -NoProfile -ExecutionPolicy Bypass -File "./Python - Voice Recorder/scripts/setup_and_test.ps1" -Action setup

install-dev:
	@powershell -NoProfile -ExecutionPolicy Bypass -File "./Python - Voice Recorder/scripts/setup_and_test.ps1" -Action install-dev

unit:
	@powershell -NoProfile -ExecutionPolicy Bypass -File "./Python - Voice Recorder/scripts/setup_and_test.ps1" -Action unit

import:
	@powershell -NoProfile -ExecutionPolicy Bypass -File "./Python - Voice Recorder/scripts/setup_and_test.ps1" -Action import

test:
	@powershell -NoProfile -ExecutionPolicy Bypass -File "./Python - Voice Recorder/scripts/setup_and_test.ps1" -Action test
