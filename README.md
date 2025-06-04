# Telegram Gift Auto Buyer

**⚠️ AI-Generated Code Notice**: This script was generated using AI assistance but has been tested. However, **ALWAYS TEST THOROUGHLY** in a safe environment before actual use.

## 🔧 Prerequisites - IMPORTANT

**Tesseract OCR is REQUIRED** - Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Installation Options:**
1. **System Installation**: Install to `C:\Program Files\Tesseract-OCR\` (recommended)
2. **Portable**: Extract to `Tesseract-OCR\` folder next to this script

The script will automatically detect Tesseract in either location.

## 🎯 What This Does

An automated tool that monitors gift prices in Telegram and purchases them when they meet your target price using OCR (Optical Character Recognition).

## ⚠️ Critical Usage Requirements

### 📱 Platform Requirements
- **ONLY works with Telegram on Android emulators** (BlueStacks, NoxPlayer, etc.)
- **Does NOT work on desktop Telegram** - PC animations interfere with price recognition
- Requires stable internet connection for reliable OCR

### 🚀 Speed Settings - READ CAREFULLY
- **Recommended: Speed 1-2 MAXIMUM**
- **Speed 3-5**: Only use if your emulator loads interface very fast OR animations are completely disabled
- Higher speeds may cause failed purchases due to timing issues
- Test extensively with small amounts before using higher speeds

### 🧪 Testing Requirements
- **Test with small gift amounts first**
- **Calibrate speed settings for your setup**
- **Verify OCR accuracy in your environment**
- **Check that all click coordinates work correctly**

## 🚀 Quick Start

1. **Install Tesseract OCR** (see links above)
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the script:**
4. **Configure in this order:**
   - Select price area (where gift prices appear)
   - Set target price (maximum you want to pay)
   - Set 4 sorting click coordinates (Sort Menu → By Date → Sort Menu → By Price)
   - Set 3 purchase click coordinates (Click Gift → Confirm → Final Buy)
5. **Test with low speeds first!**

## 🎮 How It Works

The script runs this cycle automatically:

1. **Sort by Date** → OCR price check → Buy if price ≤ target
2. **Sort by Price** → OCR price check → Buy if price ≤ target  
3. **Repeat** until stopped (ESC key)

## ⚙️ Key Features

- **Fully Autonomous**: No manual intervention needed once configured
- **OCR Price Detection**: Automatically reads prices from screen
- **Smart Speed Control**: Separate speeds for sorting vs buying actions
- **Debug Mode**: Saves OCR images for troubleshooting
- **Settings Persistence**: Remembers your configuration
- **Emergency Stop**: ESC key to stop immediately

## 🛡️ Safety Features

- Speed 3+ keeps purchase actions at normal speed (only sorting is faster)
- OCR validation before every purchase
- Manual coordinate configuration prevents accidental clicks
- Debug logging for troubleshooting


## 📋 Requirements

- Python 3.7+
- Tesseract OCR
- Android emulator with Telegram
- Stable internet connection

## ⚠️ Disclaimer

- **Educational purposes only**
- **Test thoroughly before real use**
- **Users responsible for Telegram ToS compliance**
- **Authors not liable for any damages or failed purchases**
- **Use at your own risk**

## 🐛 Troubleshooting

- **OCR not working**: Check Tesseract installation and price area selection
- **Clicks missing**: Reconfigure coordinates, ensure emulator window hasn't moved
- **Failed purchases**: Lower speed settings, check internet stability
- **Price not detected**: Ensure good contrast in selected area, disable animations

**Remember: When in doubt, use Speed 1-2 and test extensively!**
