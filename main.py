#!/usr/bin/env python3
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from phone_enum_advanced import PhoneEnumeration
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global executor for async operations
executor = ThreadPoolExecutor(max_workers=4)


class PhoneEnumBot:
    def __init__(self):
        self.enum = PhoneEnumeration(timeout=20, threads=8)
        self.app = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command"""
        welcome_text = """
🔍 **Phone Enumeration Bot** 📱

এই বটটি একটি ফোন নম্বরের সাথে যুক্ত সব কিছু খুঁজে বের করে।

**ব্যবহার করুন:**
শুধু একটি ফোন নম্বর পাঠান এবং দেখুন:
- WhatsApp Account
- Telegram Account
- Facebook Profile
- Instagram Account
- Twitter/X Account
- TikTok Account
- LinkedIn Profile
- Viber Status
- TrueCaller Info
- Possible Emails

⚠️ **শুধুমাত্র আইনি উদ্দেশ্যে ব্যবহার করুন।**

একটি ফোন নম্বর পাঠান শুরু করতে:
👉 +880 1900 000 000 (উদাহরণ)
        """
        
        keyboard = [
            [InlineKeyboardButton("সাহায্য পান", callback_data='help'),
             InlineKeyboardButton("সম্পর্কে", callback_data='about')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline buttons"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'help':
            help_text = """
**সাহায্য:**

1️⃣ ফোন নম্বর পাঠান (যেকোনো ফরম্যাটে)
2️⃣ বট স্বয়ংক্রিয়ভাবে খোঁজ করবে
3️⃣ সব প্ল্যাটফর্মে একাউন্ট দেখাবে

**ফর্ম্যাট:**
- +8801900000000
- 01900000000
- 8801900000000
- 1900000000

সবগুলোই কাজ করে! ✅
            """
            await query.edit_message_text(help_text, parse_mode='Markdown')
        
        elif query.data == 'about':
            about_text = """
📱 **Phone Enumeration Bot v1.0**

এই বট ব্যবহার করে:
- BeautifulSoup (Web Scraping)
- Requests (HTTP)
- Telegram Bot API
- OSINT Techniques

**নির্মাতা:** DADA Technology

⚠️ **দায়বদ্ধতা:** শুধুমাত্র আইনি ব্যবহার।
            """
            await query.edit_message_text(about_text, parse_mode='Markdown')
    
    def _format_results(self, results: dict) -> str:
        """Format enumeration results beautifully"""
        phone = results.get('phone', 'N/A')
        normalized = results.get('normalized_phone', 'N/A')
        
        output = f"""
╔═══════════════════════════════════════╗
║  📱 PHONE ENUMERATION RESULTS  📱     ║
╚═══════════════════════════════════════╝

📞 **আসল নম্বর:** {phone}
🌍 **স্বাভাবিক ফরম্যাট:** {normalized}

{'─' * 40}

"""
        
        platforms = results.get('platforms', {})
        found_count = 0
        
        # WhatsApp
        wa = platforms.get('whatsapp', {})
        if wa.get('found'):
            output += f"""
✅ **WhatsApp**
   • স্ট্যাটাস: {'সক্রিয়' if wa.get('active') else 'নিষ্ক্রিয়'}
   • লিংক: {wa.get('profile', {}).get('link', 'N/A')}
"""
            found_count += 1
        
        # Telegram
        tg = platforms.get('telegram', {})
        if tg.get('found'):
            output += f"""
✅ **Telegram**
   • ইউজারনেম: @{tg.get('username', 'N/A')}
   • বায়ো: {tg.get('bio', 'N/A')}
"""
            found_count += 1
        
        # Facebook
        fb = platforms.get('facebook', {})
        if fb.get('found') and fb.get('profiles'):
            output += "✅ **Facebook**\n"
            for i, profile in enumerate(fb['profiles'][:2], 1):
                output += f"   • {i}. {profile.get('name', 'N/A')}\n   Link: {profile.get('link', 'N/A')}\n"
            found_count += 1
        
        # Instagram
        ig = platforms.get('instagram', {})
        if ig.get('found') and ig.get('accounts'):
            output += "✅ **Instagram**\n"
            for i, account in enumerate(ig['accounts'][:2], 1):
                verified = "✓" if account.get('is_verified') else ""
                output += f"   • {i}. @{account.get('username', 'N/A')} {verified}\n"
                output += f"      নাম: {account.get('full_name', 'N/A')}\n"
            found_count += 1
        
        # Twitter
        tw = platforms.get('twitter', {})
        if tw.get('found') and tw.get('accounts'):
            output += "✅ **Twitter/X**\n"
            for i, account in enumerate(tw['accounts'][:2], 1):
                output += f"   • {i}. @{account.get('username', 'N/A')}\n"
            found_count += 1
        
        # TikTok
        tk = platforms.get('tiktok', {})
        if tk.get('found') and tk.get('accounts'):
            output += "✅ **TikTok**\n"
            for i, account in enumerate(tk['accounts'][:2], 1):
                output += f"   • {i}. @{account.get('username', 'N/A')}\n"
            found_count += 1
        
        # TrueCaller
        tc = platforms.get('truecaller', {})
        if tc.get('found'):
            output += f"""
✅ **TrueCaller**
   • নাম: {tc.get('name', 'N/A')}
   • ক্যারিয়ার: {tc.get('carrier', 'N/A')}
   • দেশ: {tc.get('country', 'N/A')}
"""
            found_count += 1
        
        # LinkedIn
        ln = platforms.get('linkedin', {})
        if ln.get('found') and ln.get('profiles'):
            output += "✅ **LinkedIn**\n"
            for i, profile in enumerate(ln['profiles'][:2], 1):
                output += f"   • {i}. {profile.get('name', 'N/A')}\n"
            found_count += 1
        
        # Viber
        vb = platforms.get('viber', {})
        if vb.get('found'):
            output += f"""
✅ **Viber**
   • স্ট্যাটাস: {'সক্রিয়' if vb.get('active') else 'নিষ্ক্রিয়'}
   • লিংক: {vb.get('viber_link', 'N/A')}
"""
            found_count += 1
        
        # Emails
        emails = results.get('emails', [])
        if emails:
            output += "\n✅ **সম্ভাব্য ইমেইল:**\n"
            for email in emails[:3]:
                output += f"   • {email}\n"
        
        # Summary
        output += f"""
{'─' * 40}
📊 **সারসংক্ষেপ:**
   • মোট অ্যাকাউন্ট পাওয়া: {found_count}
   • ঝুঁকি স্কোর: {results.get('risk_score', 0):.1f}%
   • স্ট্যাটাস: {results.get('status', 'Unknown')}

⚠️ শুধুমাত্র আইনি উদ্দেশ্যে ব্যবহার করুন।
        """
        
        return output
    
    async def handle_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle phone number input"""
        message = update.message.text.strip()
        
        # Validate phone format
        phone_match = re.match(r'[\d+\-\s()]+', message)
        if not phone_match or len(re.sub(r'\D', '', message)) < 10:
            await update.message.reply_text(
                "❌ অবৈধ ফোন নম্বর। সঠিক ফরম্যাটে পাঠান:\n+880190XXXXXXX অথবা 01900XXXXXX"
            )
            return
        
        phone = message
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🔍 খোঁজা হচ্ছে: {phone}\n\n⏳ এটি কয়েক সেকেন্ড সময় নিতে পারে..."
        )
        
        try:
            # Run enumeration in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                executor,
                lambda: self.enum.enumerate_all(phone)
            )
            
            # Format and send results
            formatted_results = self._format_results(results)
            
            # Split if too long (Telegram limit)
            if len(formatted_results) > 4000:
                messages = [formatted_results[i:i+4000] for i in range(0, len(formatted_results), 4000)]
                await processing_msg.delete()
                
                for msg_part in messages:
                    await update.message.reply_text(msg_part, parse_mode='Markdown')
            else:
                await processing_msg.edit_text(formatted_results, parse_mode='Markdown')
            
            logger.info(f"Enumeration completed for {phone}")
        
        except Exception as e:
            logger.error(f"Error during enumeration: {e}")
            await processing_msg.edit_text(
                f"❌ ত্রুটি ঘটেছে:\n{str(e)}\n\nকিছুক্ষণ পর আবার চেষ্টা করুন।"
            )
    
    async def setup(self) -> None:
        """Setup bot handlers"""
        self.app = Application.builder().token(TOKEN).build()
        
        # Commands
        self.app.add_handler(CommandHandler("start", self.start))
        
        # Callbacks
        self.app.add_handler(CallbackQueryHandler(self.handle_button))
        
        # Message handler for phone numbers
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_phone_number
            )
        )
        
        logger.info("Bot handlers setup complete")
    
    async def run(self) -> None:
        """Run bot"""
        await self.setup()
        logger.info("Starting bot...")
        await self.app.run_polling()


if __name__ == '__main__':
    import re
    
    bot = PhoneEnumBot()
    asyncio.run(bot.run())
