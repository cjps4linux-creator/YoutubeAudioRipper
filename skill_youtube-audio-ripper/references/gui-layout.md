# GUI Layout Specifications - YouTube Audio Ripper

## Window Configuration

- **Size**: 700x600 pixels
- **Resizable**: No (fixed size for consistent UX)
- **Theme**: Dark mode (CustomTkinter dark theme)
- **Color Theme**: Blue accent color

## Layout Structure

### Main Frame
- Padding: 20px all sides
- Fill: Both directions, expand=True

### Header Section
- **Title**: "🎵 YouTube Audio Ripper" (24pt, bold)
- **Subtitle**: "Download YouTube audio → FLAC with AI voice detection" (12pt, gray)
- **Spacing**: 5px after title, 20px after subtitle

### URL Input Section
- **Container**: CTkFrame with background color
- **Label**: "YouTube URL(s)  -  paste one or more (one per line):" (12pt, bold)
- **Text Area**: CTkTextbox, height=100, Consolas 11pt, no wrap
- **Hint**: "💡 Tip: Paste URLs directly (Ctrl+V) or enter one per line" (10pt, gray)

### Options Section
- **AI Detection Sensitivity**:
  - Label: "AI Detection Sensitivity:" (12pt)
  - Value Display: Dynamic label showing current value (12pt, bold, blue)
  - Slider: CTkSlider, range 0.3-0.9, 12 steps
  - Hint: "Lower = more sensitive | Higher = stricter" (9pt, gray)

### Progress Section
- **Container**: CTkFrame with background
- **Header**: "Progress" (12pt, bold)
- **Progress sample**: CTkProgressBar, full width
- **Status Label**: Dynamic text (10pt, gray)

### Log Section
- **Header**: "Output Log" (12pt, bold)
- **Log Area**: CTkTextbox, height=150, Consolas 10pt, disabled state

### Action Buttons Section
- **Container**: Transparent frame
- **Primary Button**: "🎵 START RIPPING 🎵" (18pt, bold, height=60, green)
  - Left-aligned, fills available space
  - Padding: 5px right
- **Secondary Buttons** (right-aligned):
  - "🗑 Clear" (14pt, height=40, gray)
  - "📁 Open Folder" (14pt, height=40, gray)
  - Padding: 5px between

## Color Scheme

### Dark Mode (Default)
- Background: #1a1a1a (CustomTkinter default)
- Frame Background: #242424 (gray17)
- Accent: #1f6aa5 (blue)
- Hover: #144870 (darkblue)
- Success/Start: #2fa572 (green)
- Success Hover: #1e7e56 (darkgreen)
- Secondary: #565b5e (gray70)
- Secondary Hover: #3d3f41 (gray30)
- Text Primary: #ffffff / #dbdbdb
- Text Secondary: #808080 (gray50)

### Light Mode
- Background: #ffffff
- Frame Background: #ebebeb (gray90)
- Accent: #3a7ebf
- Hover: #325882
- Success/Start: #2fa572
- Success Hover: #1e7e56
- Secondary: #b5b5b5
- Secondary Hover: #a5a5a5
- Text Primary: #1a1a1a
- Text Secondary: #6e6e6e

## Responsive Behavior

- Window centered on screen at startup
- All elements scale proportionally
- Minimum width: 700px
- Maximum height: 600px

## Accessibility

- High contrast colors
- Clear focus indicators
- Keyboard navigation (Tab order)
- Screen reader compatible labels
- Sufficient text sizes (min 9pt)