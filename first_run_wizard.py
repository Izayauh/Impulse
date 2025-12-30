"""
First Run Wizard for WhisperLocal
Guides new users through initial setup including microphone selection and tutorial.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

# Import from main module (will be available when bundled together)
try:
    from flow_local_dictation import (
        Theme, APP_NAME, APP_VERSION,
        list_input_devices, device_index_and_names,
        resolve_input_device, mark_first_run_complete,
        selected_input_device_idx, selected_input_device_name,
        SAMPLE_RATE, CHANNELS, get_user_data_dir
    )
    import sounddevice as sd
    import numpy as np
except ImportError:
    # Fallback for standalone testing
    print("Warning: Running wizard standalone - some features disabled")
    Theme = None
    APP_NAME = "WhisperLocal"
    APP_VERSION = "1.0.0"


class WizardTheme:
    """Theme constants for the wizard (fallback if Theme not available)."""
    BG_DARK = "#0D0D0D"
    BG_CARD = "#141414"
    BG_ELEVATED = "#1A1A1A"
    BG_HOVER = "#222222"
    PINK_PRIMARY = "#FF1493"
    PINK_LIGHT = "#FF69B4"
    PINK_DARK = "#CC1177"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    TEXT_MUTED = "#666666"
    SUCCESS = "#00E676"
    WARNING = "#FFB300"
    ERROR = "#FF5252"
    BORDER_SUBTLE = "#2A2A2A"
    FONT_FAMILY = "Segoe UI"


# Use imported Theme if available, otherwise use fallback
if Theme is None:
    Theme = WizardTheme


class FirstRunWizard:
    """Multi-step wizard for first-time setup."""
    
    def __init__(self, on_complete_callback=None):
        self.on_complete = on_complete_callback
        self.current_step = 0
        self.selected_device_idx = None
        self.selected_device_name = None
        self.create_shortcut = tk.BooleanVar(value=True)
        self.auto_start = tk.BooleanVar(value=False)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("600x500")
        self.root.configure(bg=Theme.BG_DARK)
        self.root.resizable(False, False)
        
        # Center window
        self._center_window()
        
        # Remove title bar for custom look
        self.root.overrideredirect(True)
        
        # Create custom title bar
        self._create_title_bar()
        
        # Main content frame
        self.content_frame = tk.Frame(self.root, bg=Theme.BG_DARK)
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Navigation buttons frame
        self.nav_frame = tk.Frame(self.root, bg=Theme.BG_DARK)
        self.nav_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        # Step indicators
        self.steps = ["Welcome", "Microphone", "Tutorial", "Finish"]
        self._create_step_indicators()
        
        # Start with welcome step
        self._show_step(0)
        
        # Dragging support
        self._drag_data = {"x": 0, "y": 0}
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._on_drag)
    
    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = 600
        height = 500
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_title_bar(self):
        """Create custom title bar."""
        self.title_bar = tk.Frame(self.root, bg=Theme.BG_ELEVATED, height=40)
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)
        
        # Logo
        logo = tk.Label(
            self.title_bar,
            text="◉",
            font=(Theme.FONT_FAMILY, 16),
            fg=Theme.PINK_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        logo.pack(side="left", padx=(15, 8))
        
        # Title
        title = tk.Label(
            self.title_bar,
            text=f"{APP_NAME} Setup",
            font=(Theme.FONT_FAMILY, 11, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        title.pack(side="left")
        
        # Close button
        close_btn = tk.Label(
            self.title_bar,
            text="✕",
            font=(Theme.FONT_FAMILY, 12),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=15)
        close_btn.bind("<Button-1>", lambda e: self._on_close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=Theme.ERROR))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=Theme.TEXT_SECONDARY))
    
    def _create_step_indicators(self):
        """Create step indicator dots."""
        self.step_frame = tk.Frame(self.content_frame, bg=Theme.BG_DARK)
        self.step_frame.pack(fill="x", pady=(0, 20))
        
        self.step_dots = []
        for i, step_name in enumerate(self.steps):
            dot = tk.Label(
                self.step_frame,
                text="●",
                font=(Theme.FONT_FAMILY, 10),
                fg=Theme.PINK_PRIMARY if i == 0 else Theme.TEXT_MUTED,
                bg=Theme.BG_DARK
            )
            dot.pack(side="left", padx=5)
            self.step_dots.append(dot)
            
            if i < len(self.steps) - 1:
                line = tk.Label(
                    self.step_frame,
                    text="───",
                    font=(Theme.FONT_FAMILY, 8),
                    fg=Theme.TEXT_MUTED,
                    bg=Theme.BG_DARK
                )
                line.pack(side="left")
    
    def _update_step_indicators(self):
        """Update step indicator colors."""
        for i, dot in enumerate(self.step_dots):
            if i < self.current_step:
                dot.config(fg=Theme.SUCCESS)
            elif i == self.current_step:
                dot.config(fg=Theme.PINK_PRIMARY)
            else:
                dot.config(fg=Theme.TEXT_MUTED)
    
    def _clear_content(self):
        """Clear content frame for new step."""
        for widget in self.content_frame.winfo_children():
            if widget != self.step_frame:
                widget.destroy()
        for widget in self.nav_frame.winfo_children():
            widget.destroy()
    
    def _show_step(self, step):
        """Show the specified step."""
        self.current_step = step
        self._update_step_indicators()
        self._clear_content()
        
        if step == 0:
            self._show_welcome()
        elif step == 1:
            self._show_microphone()
        elif step == 2:
            self._show_tutorial()
        elif step == 3:
            self._show_finish()
    
    def _show_welcome(self):
        """Show welcome screen."""
        # Welcome header
        header = tk.Label(
            self.content_frame,
            text=f"Welcome to {APP_NAME}!",
            font=(Theme.FONT_FAMILY, 24, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_DARK
        )
        header.pack(pady=(20, 10))
        
        # Version
        version = tk.Label(
            self.content_frame,
            text=f"Version {APP_VERSION}",
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_DARK
        )
        version.pack(pady=(0, 20))
        
        # Description
        desc_frame = tk.Frame(self.content_frame, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        desc_frame.pack(fill="x", pady=10)
        
        desc_text = """Transform your voice into text instantly - completely offline!

This wizard will help you:

  • Select your microphone
  • Learn the simple controls
  • Get ready to dictate

All speech processing happens locally on your computer.
Your voice never leaves your machine."""
        
        desc = tk.Label(
            desc_frame,
            text=desc_text,
            font=(Theme.FONT_FAMILY, 11),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_CARD,
            justify="left",
            padx=20,
            pady=20
        )
        desc.pack()
        
        # Features
        features_frame = tk.Frame(self.content_frame, bg=Theme.BG_DARK)
        features_frame.pack(fill="x", pady=20)
        
        features = [
            ("🔒", "100% Private - No cloud, no internet required"),
            ("⚡", "GPU Accelerated - Fast transcription"),
            ("🎯", "Simple Controls - Hold WIN+CTRL to speak"),
        ]
        
        for emoji, text in features:
            row = tk.Frame(features_frame, bg=Theme.BG_DARK)
            row.pack(fill="x", pady=5)
            
            icon = tk.Label(row, text=emoji, font=(Theme.FONT_FAMILY, 14), bg=Theme.BG_DARK)
            icon.pack(side="left", padx=(0, 10))
            
            label = tk.Label(
                row, text=text,
                font=(Theme.FONT_FAMILY, 10),
                fg=Theme.TEXT_SECONDARY,
                bg=Theme.BG_DARK,
                anchor="w"
            )
            label.pack(side="left", fill="x")
        
        # Next button
        self._create_nav_button("Get Started →", self._next_step, accent=True)
    
    def _show_microphone(self):
        """Show microphone selection screen."""
        header = tk.Label(
            self.content_frame,
            text="Select Your Microphone",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_DARK
        )
        header.pack(pady=(10, 5))
        
        subtitle = tk.Label(
            self.content_frame,
            text="Choose the microphone you want to use for dictation",
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK
        )
        subtitle.pack(pady=(0, 15))
        
        # Device list
        list_frame = tk.Frame(
            self.content_frame, 
            bg=Theme.BG_CARD, 
            highlightthickness=1, 
            highlightbackground=Theme.BORDER_SUBTLE
        )
        list_frame.pack(fill="both", expand=True, pady=10)
        
        # Get devices
        try:
            self.device_idxs, self.device_labels = device_index_and_names()
        except Exception:
            self.device_idxs = []
            self.device_labels = ["No devices found"]
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.device_listbox = tk.Listbox(
            list_frame,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            selectbackground=Theme.PINK_PRIMARY,
            selectforeground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 10),
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            height=8
        )
        self.device_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar.config(command=self.device_listbox.yview)
        
        for label in self.device_labels:
            self.device_listbox.insert(tk.END, label)
        
        # Pre-select first device
        if self.device_labels:
            self.device_listbox.selection_set(0)
        
        # Audio level indicator
        level_frame = tk.Frame(self.content_frame, bg=Theme.BG_DARK)
        level_frame.pack(fill="x", pady=10)
        
        level_label = tk.Label(
            level_frame,
            text="Audio Level:",
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK
        )
        level_label.pack(side="left")
        
        self.level_bar = tk.Canvas(
            level_frame, 
            width=300, 
            height=16, 
            bg=Theme.BG_ELEVATED, 
            highlightthickness=0
        )
        self.level_bar.pack(side="left", padx=10)
        self.level_fill = self.level_bar.create_rectangle(0, 0, 0, 16, fill=Theme.PINK_PRIMARY, outline="")
        
        # Test button
        self.test_btn = self._create_button(
            level_frame, "Test Mic", 
            self._test_microphone,
            side="left"
        )
        
        self.test_status = tk.Label(
            self.content_frame,
            text="",
            font=(Theme.FONT_FAMILY, 9),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK
        )
        self.test_status.pack(pady=5)
        
        # Navigation
        self._create_nav_button("← Back", self._prev_step)
        self._create_nav_button("Next →", self._apply_device_and_next, accent=True)
    
    def _test_microphone(self):
        """Test the selected microphone."""
        sel = self.device_listbox.curselection()
        if not sel or not self.device_idxs:
            self.test_status.config(text="Please select a device first", fg=Theme.WARNING)
            return
        
        device_idx = self.device_idxs[sel[0]]
        self.test_status.config(text="Testing... speak now!", fg=Theme.INFO)
        self.test_btn.config(state="disabled")
        
        def do_test():
            try:
                for _ in range(20):  # 2 seconds
                    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=device_idx) as stream:
                        block, _ = stream.read(int(SAMPLE_RATE * 0.1))
                        rms = float(np.sqrt(np.mean(block * block) + 1e-12))
                        level_pct = min(rms * 500, 300)
                        self.level_bar.coords(self.level_fill, 0, 0, level_pct, 16)
                        self.level_bar.update()
                        time.sleep(0.1)
                
                self.test_status.config(text="Test complete! Microphone is working.", fg=Theme.SUCCESS)
            except Exception as e:
                self.test_status.config(text=f"Error: {str(e)[:40]}", fg=Theme.ERROR)
            finally:
                self.test_btn.config(state="normal")
                self.level_bar.coords(self.level_fill, 0, 0, 0, 16)
        
        threading.Thread(target=do_test, daemon=True).start()
    
    def _apply_device_and_next(self):
        """Apply selected device and move to next step."""
        sel = self.device_listbox.curselection()
        if sel and self.device_idxs:
            self.selected_device_idx = self.device_idxs[sel[0]]
            self.selected_device_name = self.device_labels[sel[0]]
            
            # Save to environment for the main app
            os.environ["FLOW_INPUT_DEVICE"] = str(self.selected_device_idx)
            
            # Try to resolve in main app
            try:
                resolve_input_device()
            except Exception:
                pass
        
        self._next_step()
    
    def _show_tutorial(self):
        """Show tutorial screen."""
        header = tk.Label(
            self.content_frame,
            text="How to Use",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_DARK
        )
        header.pack(pady=(10, 20))
        
        # Tutorial steps
        steps = [
            {
                "title": "1. Position Your Cursor",
                "desc": "Click where you want the text to appear\n(text editor, email, chat, etc.)",
                "icon": "📝"
            },
            {
                "title": "2. Hold WIN + CTRL",
                "desc": "Press and hold both keys together.\nThe status bar will show \"Listening...\"",
                "icon": "⌨️"
            },
            {
                "title": "3. Speak Clearly",
                "desc": "Talk naturally into your microphone.\nSpeak at a normal pace.",
                "icon": "🎤"
            },
            {
                "title": "4. Release to Transcribe",
                "desc": "Let go of the keys when done speaking.\nText will be automatically pasted!",
                "icon": "✨"
            },
        ]
        
        for step in steps:
            step_frame = tk.Frame(
                self.content_frame, 
                bg=Theme.BG_CARD, 
                highlightthickness=1, 
                highlightbackground=Theme.BORDER_SUBTLE
            )
            step_frame.pack(fill="x", pady=5)
            
            inner = tk.Frame(step_frame, bg=Theme.BG_CARD)
            inner.pack(fill="x", padx=15, pady=10)
            
            icon = tk.Label(
                inner,
                text=step["icon"],
                font=(Theme.FONT_FAMILY, 20),
                bg=Theme.BG_CARD
            )
            icon.pack(side="left", padx=(0, 15))
            
            text_frame = tk.Frame(inner, bg=Theme.BG_CARD)
            text_frame.pack(side="left", fill="x", expand=True)
            
            title = tk.Label(
                text_frame,
                text=step["title"],
                font=(Theme.FONT_FAMILY, 11, "bold"),
                fg=Theme.PINK_PRIMARY,
                bg=Theme.BG_CARD,
                anchor="w"
            )
            title.pack(anchor="w")
            
            desc = tk.Label(
                text_frame,
                text=step["desc"],
                font=(Theme.FONT_FAMILY, 9),
                fg=Theme.TEXT_SECONDARY,
                bg=Theme.BG_CARD,
                anchor="w",
                justify="left"
            )
            desc.pack(anchor="w")
        
        # Navigation
        self._create_nav_button("← Back", self._prev_step)
        self._create_nav_button("Finish Setup →", self._next_step, accent=True)
    
    def _show_finish(self):
        """Show finish screen."""
        header = tk.Label(
            self.content_frame,
            text="You're All Set!",
            font=(Theme.FONT_FAMILY, 24, "bold"),
            fg=Theme.SUCCESS,
            bg=Theme.BG_DARK
        )
        header.pack(pady=(30, 10))
        
        check_icon = tk.Label(
            self.content_frame,
            text="✓",
            font=(Theme.FONT_FAMILY, 60),
            fg=Theme.SUCCESS,
            bg=Theme.BG_DARK
        )
        check_icon.pack(pady=20)
        
        summary = tk.Label(
            self.content_frame,
            text=f"Microphone: {self.selected_device_name or 'Default'}\n\nHold WIN + CTRL to start dictating!",
            font=(Theme.FONT_FAMILY, 12),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            justify="center"
        )
        summary.pack(pady=10)
        
        # Options frame
        options_frame = tk.Frame(self.content_frame, bg=Theme.BG_DARK)
        options_frame.pack(pady=20)
        
        # Desktop shortcut option
        shortcut_check = tk.Checkbutton(
            options_frame,
            text="Create Desktop Shortcut",
            variable=self.create_shortcut,
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            selectcolor=Theme.BG_ELEVATED,
            activebackground=Theme.BG_DARK,
            activeforeground=Theme.TEXT_PRIMARY
        )
        shortcut_check.pack(anchor="w", pady=2)
        
        # Auto-start option
        autostart_check = tk.Checkbutton(
            options_frame,
            text="Start with Windows",
            variable=self.auto_start,
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            selectcolor=Theme.BG_ELEVATED,
            activebackground=Theme.BG_DARK,
            activeforeground=Theme.TEXT_PRIMARY
        )
        autostart_check.pack(anchor="w", pady=2)
        
        # Finish button
        self._create_nav_button("Start Using WhisperLocal", self._finish, accent=True, center=True)
    
    def _create_button(self, parent, text, command, side="left"):
        """Create a styled button."""
        btn = tk.Label(
            parent,
            text=text,
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2",
            padx=15,
            pady=8
        )
        btn.pack(side=side, padx=5)
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=Theme.BG_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=Theme.BG_ELEVATED))
        return btn
    
    def _create_nav_button(self, text, command, accent=False, center=False):
        """Create a navigation button."""
        btn = tk.Label(
            self.nav_frame,
            text=text,
            font=(Theme.FONT_FAMILY, 11),
            fg=Theme.BG_DARK if accent else Theme.TEXT_PRIMARY,
            bg=Theme.PINK_PRIMARY if accent else Theme.BG_ELEVATED,
            cursor="hand2",
            padx=20,
            pady=10
        )
        
        if center:
            btn.pack(pady=10)
        elif accent:
            btn.pack(side="right", padx=5)
        else:
            btn.pack(side="left", padx=5)
        
        if accent:
            btn.bind("<Enter>", lambda e: btn.config(bg=Theme.PINK_LIGHT))
            btn.bind("<Leave>", lambda e: btn.config(bg=Theme.PINK_PRIMARY))
        else:
            btn.bind("<Enter>", lambda e: btn.config(bg=Theme.BG_HOVER))
            btn.bind("<Leave>", lambda e: btn.config(bg=Theme.BG_ELEVATED))
        
        btn.bind("<Button-1>", lambda e: command())
        return btn
    
    def _next_step(self):
        """Move to next step."""
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
    
    def _prev_step(self):
        """Move to previous step."""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
    
    def _finish(self):
        """Finish the wizard and apply settings."""
        # Create desktop shortcut if requested
        if self.create_shortcut.get():
            self._create_desktop_shortcut()
        
        # Set up auto-start if requested
        if self.auto_start.get():
            self._setup_auto_start()
        
        # Mark first run complete
        try:
            mark_first_run_complete()
        except Exception:
            pass
        
        # Close wizard
        self.root.destroy()
        
        # Call completion callback
        if self.on_complete:
            self.on_complete()
    
    def _create_desktop_shortcut(self):
        """Create a desktop shortcut (Windows)."""
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = sys.executable
            shortcut.WorkingDirectory = os.path.dirname(sys.executable)
            shortcut.IconLocation = sys.executable
            shortcut.Description = "WhisperLocal - Voice to Text"
            shortcut.save()
        except ImportError:
            # winshell not available - skip
            pass
        except Exception as e:
            print(f"Could not create shortcut: {e}")
    
    def _setup_auto_start(self):
        """Set up auto-start on Windows."""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{sys.executable}"')
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Could not set auto-start: {e}")
    
    def _start_drag(self, event):
        """Start window drag."""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def _on_drag(self, event):
        """Handle window dragging."""
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")
    
    def _on_close(self):
        """Handle window close."""
        if messagebox.askyesno(
            "Skip Setup?",
            "Are you sure you want to skip the setup?\n\nYou can access settings later with WIN+CTRL+S."
        ):
            # Mark as complete anyway to avoid showing again
            try:
                mark_first_run_complete()
            except Exception:
                pass
            self.root.destroy()
            if self.on_complete:
                self.on_complete()
    
    def run(self):
        """Run the wizard."""
        self.root.mainloop()


def show_first_run_wizard(on_complete=None):
    """Show the first run wizard."""
    wizard = FirstRunWizard(on_complete_callback=on_complete)
    wizard.run()


if __name__ == "__main__":
    # Standalone test
    show_first_run_wizard(on_complete=lambda: print("Setup complete!"))

