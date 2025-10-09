"""
Cloud UI Components for Voice Recorder Pro

Provides user interface elements for cloud authentication,
file management, and premium feature access.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QProgressBar, QMessageBox,
    QTextEdit, QLineEdit, QFormLayout,
    QFrame
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont

from .auth_manager import GoogleAuthManager
from .drive_manager import GoogleDriveManager
from .feature_gate import FeatureGate

class CloudUploadThread(QThread):
    """Background thread for cloud uploads using the new Uploader interface.

    This thread calls drive_manager.get_uploader().upload(...) so new code
    uses the typed contract and exceptions. For legacy callers we still
    support a fallback via drive_manager.upload_recording_legacy when
    the manager doesn't expose `get_uploader()`.
    """

    progress_updated = Signal(int)  # Progress percentage
    upload_finished = Signal(bool, str)  # Success, message
    duplicate_detected = Signal(str, str)  # file_id, name

    def __init__(self, drive_manager: 'GoogleDriveManager', file_path: str, title: str | None = None, description: str | None = None, tags: list[str] | None = None):
        super().__init__()
        self.drive_manager = drive_manager
        self.file_path = file_path
        self.title = title
        self.description = description
        self.tags = tags
        self._cancel_event = None

    def run(self):
        """Execute upload in background using Uploader or legacy shim."""
        try:
            # Try to obtain a typed uploader from the manager if available
            uploader = None
            try:
                uploader = getattr(self.drive_manager, 'get_uploader', None)
                if callable(uploader):
                    uploader = self.drive_manager.get_uploader()
                else:
                    uploader = None
            except Exception:
                uploader = None

            # Prepare cancel event for long-running uploads
            import threading
            cancel_event = threading.Event()
            self._cancel_event = cancel_event

            def progress_cb(progress_dict: dict):
                try:
                    pct = progress_dict.get('percent')
                    if pct is None and progress_dict.get('total_bytes'):
                        total = progress_dict.get('total_bytes')
                        uploaded = progress_dict.get('uploaded_bytes', 0)
                        pct = int(uploaded * 100 / total) if total else 0
                    if pct is None:
                        pct = 0
                    self.progress_updated.emit(int(pct))
                except Exception:
                    # Swallow progress callback errors; don't crash the thread
                    pass

            if uploader is not None:
                # Use the new uploader interface which raises typed exceptions
                try:
                    result = uploader.upload(
                        self.file_path,
                        title=self.title,
                        description=self.description,
                        tags=self.tags,
                        progress_callback=progress_cb,
                        cancel_event=cancel_event,
                    )
                except Exception as e:
                    # Detect duplicate and emit a specific signal so the UI can prompt
                    try:
                        from .exceptions import DuplicateFoundError
                        if isinstance(e, DuplicateFoundError):
                            self.duplicate_detected.emit(getattr(e, 'file_id', ''), getattr(e, 'name', ''))
                            return
                    except Exception:
                        pass
                    raise

                file_id = result.get('file_id') if result else None

            else:
                # Fallback to legacy behaviour for older managers
                try:
                    file_id = self.drive_manager.upload_recording_legacy(
                        self.file_path, title=self.title, description=self.description, tags=self.tags
                    )
                except Exception:
                    file_id = None

            if file_id:
                self.upload_finished.emit(True, f"✅ Upload successful! File ID: {file_id}")
            else:
                self.upload_finished.emit(False, "❌ Upload failed. Please try again.")

        except Exception as e:
            # Surface typed exceptions' messages to the UI
            try:
                self.upload_finished.emit(False, f"❌ Upload error: {str(e)}")
            except Exception:
                # Last-resort: log nothing to avoid raising from thread
                pass

    def cancel(self) -> None:
        """Signal cancellation to the running upload if one is active."""
        try:
            if self._cancel_event is not None:
                self._cancel_event.set()
        except Exception:
            pass

class CloudAuthWidget(QWidget):
    """Authentication section for cloud features"""
    
    auth_changed = Signal(bool)  # Authentication status changed
    
    def __init__(self, auth_manager: GoogleAuthManager, feature_gate: FeatureGate):
        super().__init__()
        self.auth_manager = auth_manager
        self.feature_gate = feature_gate
        self.init_ui()
        self.update_auth_status()
    
    def init_ui(self):
        """Initialize authentication UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🔐 Cloud Authentication")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Status display
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                background-color: #f0f0f0;
                color: #333;
            }
        """)
        layout.addWidget(self.status_label)
        
        # User info section (hidden when not authenticated)
        self.user_info_widget = QWidget()
        user_info_layout = QHBoxLayout(self.user_info_widget)
        
        self.user_avatar = QLabel()
        self.user_avatar.setFixedSize(48, 48)
        self.user_avatar.setStyleSheet("border-radius: 24px; border: 2px solid #ddd;")
        user_info_layout.addWidget(self.user_avatar)
        
        user_details_layout = QVBoxLayout()
        self.user_name = QLabel()
        self.user_name.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.user_email = QLabel()
        self.user_email.setStyleSheet("color: #666;")
        user_details_layout.addWidget(self.user_name)
        user_details_layout.addWidget(self.user_email)
        user_info_layout.addLayout(user_details_layout)
        
        layout.addWidget(self.user_info_widget)
        
        # Action button
        self.auth_button = QPushButton()
        self.auth_button.clicked.connect(self.on_auth_button_clicked)
        layout.addWidget(self.auth_button)
        
        # Tier status
        self.tier_label = QLabel()
        self.tier_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tier_label.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                border-radius: 12px;
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.tier_label)
        
        self.setLayout(layout)
    
    def update_auth_status(self):
        """Update UI based on authentication status"""
        is_authenticated = self.auth_manager.is_authenticated()
        
        if is_authenticated:
            # Authenticated state
            user_info = self.auth_manager.get_user_info()
            if user_info:
                self.status_label.setText(f"✅ Signed in as {user_info['name']}")
                self.user_name.setText(user_info['name'])
                self.user_email.setText(user_info['email'])
                
                # TODO: Load user avatar from URL
                self.user_avatar.setText("👤")
                self.user_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                self.status_label.setText("✅ Authenticated")
            
            self.auth_button.setText("🚪 Sign Out")
            self.user_info_widget.show()
            
        else:
            # Not authenticated state
            self.status_label.setText("🔒 Not signed in - Limited features available")
            self.auth_button.setText("🔐 Sign in with Google")
            self.user_info_widget.hide()
        
        # Update tier status
        tier_text = self.feature_gate.get_tier_status_text()
        self.tier_label.setText(tier_text)
        
        self.auth_changed.emit(is_authenticated)
    
    def on_auth_button_clicked(self):
        """Handle authentication button click"""
        if self.auth_manager.is_authenticated():
            # Sign out
            reply = QMessageBox.question(
                self, "Sign Out", 
                "Are you sure you want to sign out?\n\nThis will disable cloud features.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.auth_manager.logout():
                    QMessageBox.information(self, "Signed Out", "✅ Successfully signed out")
                    self.update_auth_status()
                else:
                    QMessageBox.warning(self, "Error", "❌ Failed to sign out")
        else:
            # Sign in
            self.auth_button.setEnabled(False)
            self.auth_button.setText("🔄 Signing in...")
            
            # Start authentication in separate thread to avoid blocking UI
            QTimer.singleShot(100, self.do_authentication)
    
    def do_authentication(self):
        """Perform authentication"""
        try:
            if self.auth_manager.authenticate():
                QMessageBox.information(self, "Authentication Success", "✅ Successfully signed in!")
                self.update_auth_status()
            else:
                QMessageBox.warning(self, "Authentication Failed", "❌ Failed to sign in. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "Authentication Error", f"❌ Error: {str(e)}")
        finally:
            self.auth_button.setEnabled(True)
            self.update_auth_status()

class CloudUploadWidget(QWidget):
    """Widget for uploading recordings to cloud"""
    
    upload_completed = Signal(bool, str)  # Success, message
    
    def __init__(self, drive_manager: GoogleDriveManager, feature_gate: FeatureGate):
        super().__init__()
        self.drive_manager = drive_manager
        self.feature_gate = feature_gate
        self.current_file_path: str | None = None
        self.upload_thread = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize upload UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("☁️ Cloud Upload")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 4px; background-color: #f5f5f5; border-radius: 4px;")
        file_layout.addWidget(self.file_label)
        
        self.select_button = QPushButton("📁 Select File")
        self.select_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.select_button)
        
        layout.addLayout(file_layout)
        
        # Metadata inputs
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Optional: Custom title for recording")
        form_layout.addRow("Title:", self.title_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        self.description_input.setPlaceholderText("Optional: Description or notes")
        form_layout.addRow("Description:", self.description_input)
        
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Optional: Tags separated by commas")
        form_layout.addRow("Tags:", self.tags_input)
        
        layout.addLayout(form_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Upload button
        self.upload_button = QPushButton("📤 Upload to Google Drive")
        self.upload_button.clicked.connect(self.start_upload)
        self.upload_button.setEnabled(False)
        layout.addWidget(self.upload_button)

        # Jobs button to view background upload jobs
        from .job_dialog import JobDialog
        self.jobs_button = QPushButton("Jobs...")
        try:
            # Temporary debug info to verify DB paths at runtime
            from models import database as _db
            from . import job_queue_sql as _jq
            print(f"[debug] models.DATABASE_URL={_db.DATABASE_URL}")
            print(f"[debug] job_queue_sql.DEFAULT_DB={repr(_jq.DEFAULT_DB)}")
        except Exception:
            pass
        self.jobs_button.clicked.connect(lambda: JobDialog(self).exec())
        layout.addWidget(self.jobs_button)

        # Cancel upload button (hidden until upload starts)
        self.cancel_button = QPushButton("✖ Cancel")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
    
    def select_file(self):
        """Select file for upload"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Recording",
            "", "Audio Files (*.wav *.mp3 *.flac *.m4a);;All Files (*)"
        )
        
        if file_path:
            self.current_file_path = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            self.file_label.setText(f"📄 {file_name} ({file_size:.1f} MB)")
            self.upload_button.setEnabled(True)
            
            # Auto-fill title if empty
            if not self.title_input.text():
                name_without_ext = os.path.splitext(file_name)[0]
                self.title_input.setText(name_without_ext)
    
    def start_upload(self):
        """Start uploading file to cloud"""
        if not self.current_file_path:
            QMessageBox.warning(self, "No File", "Please select a file to upload")
            return
        
        if not self.feature_gate.can_upload_to_cloud():
            restriction_msg = self.feature_gate.get_restriction_message('cloud_upload')
            QMessageBox.information(self, "Feature Restricted", restriction_msg or "Feature not available")
            return

        # Ensure user is authenticated before attempting upload. The Drive manager
        # will raise NotAuthenticatedError if auth is missing but we proactively
        # check and prompt the user here to provide a better UX.
        auth_manager = getattr(self.drive_manager, 'auth_manager', None)
        if auth_manager is None or not auth_manager.is_authenticated():
            reply = QMessageBox.question(
                self,
                "Sign in required",
                "You must sign in with Google to upload recordings. Sign in now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Run authentication asynchronously to avoid blocking UI
            self.upload_button.setEnabled(False)
            self.upload_button.setText("🔄 Signing in...")
            QTimer.singleShot(100, self.do_auth_and_start_upload)
            return

    def do_auth_and_start_upload(self):
        """Perform authentication then continue with upload if successful."""
        auth_manager = getattr(self.drive_manager, 'auth_manager', None)
        try:
            success = False
            if auth_manager:
                success = auth_manager.authenticate()

            if success:
                QMessageBox.information(self, "Authentication Success", "✅ Successfully signed in!")
                # Proceed with upload now that user is authenticated
                QTimer.singleShot(100, self.start_upload)
            else:
                QMessageBox.warning(self, "Authentication Failed", "❌ Failed to sign in. Upload cancelled.")
        except Exception as e:
            QMessageBox.critical(self, "Authentication Error", f"❌ Error: {str(e)}")
        finally:
            # Restore upload button state; start_upload will manage actual upload UI
            self.upload_button.setEnabled(True)
            self.upload_button.setText("📤 Upload to Google Drive")
        
        # Prepare upload data
        title = self.title_input.text().strip() or None
        description = self.description_input.toPlainText().strip() or None
        tags_text = self.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else None
        
        # Start upload thread
        self.upload_thread = CloudUploadThread(
            self.drive_manager, self.current_file_path, title, description, tags
        )
        self.upload_thread.progress_updated.connect(self.update_progress)
        self.upload_thread.upload_finished.connect(self.upload_finished)
        self.upload_thread.duplicate_detected.connect(self.on_duplicate_detected)

        # Expose cancel button
        self.cancel_button.show()
        self.cancel_button.setEnabled(True)
        
        # Update UI for upload state
        self.upload_button.setEnabled(False)
        self.upload_button.setText("🔄 Uploading...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.upload_thread.start()

    def on_duplicate_detected(self, file_id: str, name: str) -> None:
        """Prompt user when a duplicate is detected during upload."""
        reply = QMessageBox.question(
            self,
            "Duplicate Found",
            f"A file named '{name or 'unknown'}' already exists in Drive (ID: {file_id}).\n\nDo you want to open the existing file in browser instead of uploading?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Open browser to the file's Drive URL if possible
            import webbrowser
            webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")
            self.upload_finished(True, f"Opened existing file: {file_id}")
        elif reply == QMessageBox.StandardButton.No:
            # User chose to force upload: restart upload with force flag via job queue
            try:
                from .job_queue_sql import enqueue_job, JobRow
                import uuid
                job = JobRow(id=str(uuid.uuid4()), file_path=self.current_file_path, title=self.title_input.text() or None, description=self.description_input.toPlainText() or None, tags=[t.strip() for t in (self.tags_input.text() or '').split(',') if t.strip()])
                enqueue_job(job)
                QMessageBox.information(self, "Queued", "Upload has been queued and will be retried.")
                self.upload_finished(True, "Upload queued")
            except Exception as e:
                QMessageBox.warning(self, "Queue Error", f"Failed to enqueue upload: {e}")
        else:
            # Cancelled by user
            self.upload_finished(False, "Upload cancelled by user due to duplicate")

    def on_show_jobs_clicked(self):
        """Show a simple job status dialog listing recent jobs."""
        try:
            from .job_queue_sql import get_all_jobs
            jobs = get_all_jobs()
            lines = []
            for j in jobs[:50]:
                lines.append(f"{j.id[:8]}  {j.status}  attempts={j.attempts}/{j.max_attempts}  {j.file_path}")
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Upload Jobs")
            dlg.setText("\n".join(lines) or "No jobs found")
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to list jobs: {e}")
    
    def update_progress(self, percentage: int) -> None:
        """Update upload progress"""
        self.progress_bar.setValue(percentage)
    
    def upload_finished(self, success: bool, message: str) -> None:
        """Handle upload completion"""
        self.upload_button.setEnabled(True)
        self.upload_button.setText("📤 Upload to Google Drive")
        self.progress_bar.hide()
        # Hide/disable cancel button
        try:
            self.cancel_button.hide()
            self.cancel_button.setEnabled(False)
        except Exception:
            pass
        
        if success:
            QMessageBox.information(self, "Upload Complete", message)
            # Clear form
            self.current_file_path = None
            self.file_label.setText("No file selected")
            self.title_input.clear()
            self.description_input.clear()
            self.tags_input.clear()
            self.upload_button.setEnabled(False)
        else:
            QMessageBox.warning(self, "Upload Failed", message)
        
        self.upload_completed.emit(success, message)
    
    def set_current_recording(self, file_path: str | None):
        """Set current recording for quick upload"""
        if file_path and os.path.exists(file_path):
            self.current_file_path = file_path
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            self.file_label.setText(f"📄 {file_name} ({file_size:.1f} MB)")
            self.upload_button.setEnabled(True)
            
            # Auto-fill title
            name_without_ext = os.path.splitext(file_name)[0]
            self.title_input.setText(name_without_ext)

    def on_cancel_clicked(self):
        """Called when user clicks Cancel; signal the upload thread to cancel."""
        if self.upload_thread and hasattr(self.upload_thread, 'cancel'):
            try:
                self.upload_thread.cancel()
                self.cancel_button.setEnabled(False)
                self.progress_bar.setFormat('Cancelling...')
            except Exception:
                pass

class CloudUI(QWidget):
    """Main cloud features UI container"""
    
    def __init__(self, auth_manager: GoogleAuthManager, drive_manager: GoogleDriveManager, feature_gate: FeatureGate):
        super().__init__()
        self.auth_manager = auth_manager
        self.drive_manager = drive_manager
        self.feature_gate = feature_gate
        self.init_ui()
    
    def init_ui(self):
        """Initialize cloud UI"""
        main_layout = QVBoxLayout()
        
        # Cloud section header
        header = QLabel("☁️ Cloud Features")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #1976d2; margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        # Authentication widget
        self.auth_widget = CloudAuthWidget(self.auth_manager, self.feature_gate)
        self.auth_widget.auth_changed.connect(self.on_auth_changed)
        main_layout.addWidget(self.auth_widget)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # Upload widget
        self.upload_widget = CloudUploadWidget(self.drive_manager, self.feature_gate)
        main_layout.addWidget(self.upload_widget)
        
        # Feature preview for free users
        self.preview_widget = self.create_feature_preview()
        main_layout.addWidget(self.preview_widget)
        
        self.setLayout(main_layout)
        self.update_visibility()
    
    def create_feature_preview(self):
        """Create feature preview for non-authenticated users"""
        widget = QGroupBox("⭐ Premium Cloud Features")
        layout = QVBoxLayout(widget)
        
        benefits = self.feature_gate.get_upgrade_benefits()
        
        if benefits:
            for benefit in benefits[:6]:  # Show first 6 benefits
                benefit_label = QLabel(benefit)
                benefit_label.setStyleSheet("color: #666; margin: 2px 0;")
                layout.addWidget(benefit_label)
        
        upgrade_button = QPushButton("🚀 Sign in to Enable Premium Features")
        upgrade_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        upgrade_button.clicked.connect(self.auth_widget.on_auth_button_clicked)
        layout.addWidget(upgrade_button)
        
        return widget
    
    def on_auth_changed(self, is_authenticated: bool):
        """Handle authentication status change"""
        self.update_visibility()
    
    def update_visibility(self):
        """Update widget visibility based on authentication"""
        is_authenticated = self.auth_manager.is_authenticated()
        
        # Show/hide widgets based on authentication
        self.upload_widget.setVisible(is_authenticated)
        self.preview_widget.setVisible(not is_authenticated)
    
    def set_current_recording(self, file_path: str | None):
        """Set current recording for upload widget"""
        self.upload_widget.set_current_recording(file_path)

# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from config_manager import config_manager

    app = QApplication(sys.argv)

    # Initialize managers
    auth_manager = GoogleAuthManager(use_keyring=config_manager.prefers_keyring())
    drive_manager = GoogleDriveManager(auth_manager)
    feature_gate = FeatureGate(auth_manager)
    
    # Create and show cloud UI
    cloud_ui = CloudUI(auth_manager, drive_manager, feature_gate)
    cloud_ui.setWindowTitle("Voice Recorder Pro - Cloud Features")
    cloud_ui.setMinimumSize(400, 600)
    cloud_ui.show()
    
    sys.exit(app.exec())
