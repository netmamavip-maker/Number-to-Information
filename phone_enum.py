#!/usr/bin/env python3
import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
import asyncio
from phone_enum import PhoneEnumeration
import re

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token (set as environment variable)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Your Render app URL

# Admin user IDs (add yours)
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]

class TelegramPhoneEnumBot:
    def __init__(self):
        self.enum_tool = PhoneEnumeration(timeout=15, threads=5)
        self.active_enums = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user_id = update.effective_user.id
        
        welcome_text = """
🔍 *Phone Enumeration Bot*

এই বট এর মাধ্যমে যেকোনো নম্বর দিয়ে সব সোশ্যাল মিডিয়া অ্যাকাউন্ট খুঁজে বের করুন।

📱 *কীভাবে ব্যবহার করবেন:*

1️⃣ একটি ফোন নম্বর পাঠান:
`+8801900000000` অথবা `01900000000`

2️⃣ বট সব প্ল্যাটফর্মে খুঁজবে:
• Facebook
• WhatsApp
• Telegram
• Instagram
• LinkedIn
• TrueCaller
• Viber
• TikTok
• Twitter

3️⃣ কয়েক সেকেন্ডে সব ফলাফল পাবেন ✓

⚠️ শুধুমাত্র আইনি ব্যবহারের জন্য।

*এখনই শুরু করুন:*
"""
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Validate phone number
        if not self._is_valid_phone(message_text):
            await update.message.reply_text(
                "❌ Invalid phone number.\n\nব্যবহার করুন:\n`+8801900000000`\nঅথবা\n`01900000000`",
                parse_mode='Markdown'
            )
            return
        
        # Normalize
        phone = self.enum_tool.normalize_phone(message_text)
        
        # Send loading message
        loading_msg = await update.message.reply_text(
            f"🔍 Searching for accounts linked to: {phone}\n\n"
            f"এটি কয়েক সেকেন্ড সময় নিতে পারে...",
            parse_mode='Markdown'
        )
        
        # Store active enum
        self.active_enums[user_id] = {
            'phone': phone,
            'status': 'running',
            'message_id': loading_msg.message_id
        }
        
        try:
            # Run enumeration (async)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.enum_tool.enumerate_all, phone)
            
            # Format results
            results_text = self._format_results(self.enum_tool.results)
            
            # Send results
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                text=results_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Save results to file
            self._save_results(phone, self.enum_tool.results)
            
            self.active_enums[user_id]['status'] = 'completed'
        
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                text=f"❌ Error: {str(e)[:100]}",
                parse_mode='Markdown'
            )
            self.active_enums[user_id]['status'] = 'error'
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        cleaned = re.sub(r'\D', '', phone)
        return 10 <= len(cleaned) <= 13
    
    def _format_results(self, results: dict) -> str:
        """Format results for Telegram"""
        phone = results.get('phone', 'N/A')
        
        text = f"📱 *Phone Enumeration Results*\n"
        text += f"*Number:* `{phone}`\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        found_count = 0
        
        # Facebook
        fb = results.get('facebook', {})
        if fb.get('accounts'):
            found_count += len(fb['accounts'])
            text += "✅ *FACEBOOK* Found\n"
            for acc in fb['accounts'][:3]:
                url = acc.get('profile_url', '#')
                text += f"  • [{acc.get('profile_id')}]({url})\n"
            if len(fb['accounts']) > 3:
                text += f"  ... +{len(fb['accounts'])-3} more\n"
            text += "\n"
        
        # WhatsApp
        wa = results.get('whatsapp', {})
        if wa.get('account_active'):
            found_count += 1
            text += "✅ *WHATSAPP* Active\n"
            if wa.get('profile_info', {}).get('status'):
                text += f"  • Status: `{wa['profile_info']['status']}`\n"
            if wa.get('profile_info', {}).get('name'):
                text += f"  • Name: `{wa['profile_info']['name']}`\n"
            wa_link = wa.get('profile_info', {}).get('wa_link')
            if wa_link:
                text += f"  • [Open WhatsApp]({wa_link})\n"
            text += "\n"
        
        # Telegram
        tg = results.get('telegram', {})
        if tg.get('accounts'):
            found_count += len(tg['accounts'])
            text += "✅ *TELEGRAM* Found\n"
            for acc in tg['accounts'][:3]:
                url = acc.get('url', '#')
                text += f"  • [@{acc.get('username')}]({url})\n"
                if acc.get('bio'):
                    text += f"    Bio: `{acc['bio'][:50]}`\n"
            text += "\n"
        
        # Instagram
        ig = results.get('instagram', {})
        if ig.get('accounts'):
            found_count += len(ig['accounts'])
            text += "✅ *INSTAGRAM* Found\n"
            for acc in ig['accounts'][:3]:
                url = acc.get('profile_url', '#')
                text += f"  • [@{acc.get('username')}]({url})\n"
            text += "\n"
        
        # LinkedIn
        li = results.get('linkedin', {})
        if li.get('profiles'):
            found_count += len(li['profiles'])
            text += "✅ *LINKEDIN* Found\n"
            for prof in li['profiles'][:3]:
                url = prof.get('profile_url', '#')
                text += f"  • [{prof.get('profile_id')}]({url})\n"
            text += "\n"
        
        # TrueCaller
        tc = results.get('truecaller', {})
        if tc.get('profile'):
            found_count += 1
            text += "✅ *TRUECALLER* Found\n"
            text += f"  • Name: `{tc['profile'].get('name')}`\n"
            if tc['profile'].get('category'):
                text += f"  • Category: `{tc['profile']['category']}`\n"
            text += "\n"
        
        # Viber
        vb = results.get('viber', {})
        if vb.get('account_active'):
            found_count += 1
            text += "✅ *VIBER* Active\n"
            if vb.get('viber_link'):
                text += f"  • [Open Viber]({vb['viber_link']})\n"
            text += "\n"
        
        # TikTok
        tt = results.get('tiktok', {})
        if tt.get('accounts'):
            found_count += len(tt['accounts'])
            text += "✅ *TIKTOK* Found\n"
            for acc in tt['accounts'][:3]:
                url = acc.get('profile_url', '#')
                text += f"  • [@{acc.get('username')}]({url})\n"
            text += "\n"
        
        # Twitter
        tw = results.get('twitter', {})
        if tw.get('accounts'):
            found_count += len(tw['accounts'])
            text += "✅ *TWITTER* Found\n"
            for acc in tw['accounts'][:3]:
                url = acc.get('profile_url', '#')
                text += f"  • [@{acc.get('handle')}]({url})\n"
            text += "\n"
        
        # Summary
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"*Total Accounts Found: {found_count}*\n\n"
        text += "⚠️ শুধুমাত্র আইনি ব্যবহারের জন্য।"
        
        return text
    
    def _save_results(self, phone: str, results: dict):
        """Save results to file"""
        phone_clean = re.sub(r'\D', '', phone)
        filename = f"results_{phone_clean}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Error handler"""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    def run(self):
        """Run the bot"""
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone_input))
        app.add_error_handler(self.error_handler)
        
        # Start bot
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = TelegramPhoneEnumBot()
    bot.run()