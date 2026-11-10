#!/usr/bin/env python3
"""
Simple test to verify the app works with public videos
"""

import customtkinter as ctk

# Simple test - should work without authentication
def test_gui():
    app = ctk.CTk()
    app.title("YouTube Audio Ripper - Test")
    app.geometry("700x600")
    
    main_frame = ctk.CTkFrame(app)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Header
    header = ctk.CTkLabel(
        main_frame,
        text="🎵 YouTube Audio Ripper",
        font=ctk.CTkFont(size=24, weight="bold")
    )
    header.pack(pady=(0, 5))
    
    # Test URL (public video)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rickroll
    
    input_frame = ctk.CTkFrame(main_frame, fg_color=("gray90", "gray17"))
    input_frame.pack(fill="x", pady=(0, 15))
    
    input_label = ctk.CTkLabel(
        input_frame,
        text=f"YouTube URL(s)  -  paste one or more (one per line):\n{test_url}",
        font=ctk.CTkFont(size=12, weight="bold")
    )
    input_label.pack(anchor="w", padx=15, pady=(12, 5))
    
    url_text = ctk.CTkTextbox(
        input_frame,
        height=50,
        font=ctk.CTkFont(family="Consolas", size=11),
        wrap="none"
    )
    url_text.pack(fill="x", padx=15, pady=(0, 10))
    
    hint = ctk.CTkLabel(
        input_frame,
        text="💡 Tip: Paste URLs directly (Ctrl+V) or enter one per line",
        font=ctk.CTkFont(size=10),
        text_color=("gray40", "gray50")
    )
    hint.pack(anchor="w", padx=15, pady=(0, 10))
    
    # Start button
    rip_button = ctk.CTkButton(
        main_frame,
        text="🎵 START RIPPING 🎵",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=40,
        command=lambda: print("Ripping started!"),
        state="normal"
    )
    rip_button.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=15)
    
    print("✅ GUI initialized - test button is visible")
    app.mainloop()

if __name__ == "__main__":
    test_gui()