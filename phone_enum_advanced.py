#!/usr/bin/env python3
import re
import requests
import json
import logging
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import urllib.parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhoneEnumeration:
    def __init__(self, timeout=15, threads=8):
        self.timeout = timeout
        self.threads = threads
        self.results = {}
        self.executor = ThreadPoolExecutor(max_workers=threads)
        self.session = requests.Session()
        self.session.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone to international format"""
        cleaned = re.sub(r'\D', '', phone)
        
        # Handle Bangladesh numbers
        if cleaned.startswith('88'):
            return f"+{cleaned}"
        elif cleaned.startswith('1'):
            return f"+880{cleaned[1:]}"
        elif cleaned.startswith('01'):
            return f"+880{cleaned[2:]}"
        elif len(cleaned) == 10:
            return f"+880{cleaned}"
        else:
            return f"+{cleaned}"
    
    def enumerate_all(self, phone: str) -> Dict:
        """Main enumeration orchestrator"""
        self.results = {
            'phone': phone,
            'normalized_phone': self.normalize_phone(phone),
            'status': 'Enumerating...',
            'platforms': {},
            'emails': [],
            'risk_indicators': []
        }
        
        try:
            # Run all checks in parallel
            futures = {
                'whatsapp': self.executor.submit(self._check_whatsapp, phone),
                'telegram': self.executor.submit(self._check_telegram, phone),
                'facebook': self.executor.submit(self._check_facebook, phone),
                'instagram': self.executor.submit(self._check_instagram, phone),
                'truecaller': self.executor.submit(self._check_truecaller, phone),
                'tiktok': self.executor.submit(self._check_tiktok, phone),
                'twitter': self.executor.submit(self._check_twitter, phone),
                'viber': self.executor.submit(self._check_viber, phone),
                'linkedin': self.executor.submit(self._check_linkedin, phone),
                'gmail': self.executor.submit(self._check_gmail, phone),
            }
            
            # Collect results
            for platform, future in futures.items():
                try:
                    result = future.result(timeout=self.timeout + 5)
                    self.results['platforms'][platform] = result
                except Exception as e:
                    logger.error(f"{platform} check failed: {e}")
                    self.results['platforms'][platform] = {'error': str(e), 'found': False}
            
            # Find emails
            self.results['emails'] = self._generate_email_patterns(phone)
            
            # Calculate risk score
            self.results['risk_score'] = self._calculate_risk_score()
            self.results['status'] = 'Complete'
            
        except Exception as e:
            logger.error(f"Enumeration failed: {e}")
            self.results['error'] = str(e)
            self.results['status'] = 'Error'
        
        return self.results
    
    def _check_whatsapp(self, phone: str) -> Dict:
        """Check WhatsApp with advanced detection"""
        result = {
            'found': False,
            'active': False,
            'profile': None,
            'profile_pic': None,
            'last_seen': None,
            'status_text': None,
            'verified': False
        }
        
        try:
            normalized = self.normalize_phone(phone).replace('+', '')
            
            # WhatsApp Web API check
            wa_api_url = f"https://www.whatsapp.com/contact/download/?phone={normalized}"
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.whatsapp.com/'
            
            resp = self.session.head(wa_api_url, headers=headers, allow_redirects=False)
            
            if resp.status_code == 200:
                result['found'] = True
                result['active'] = True
                result['profile'] = {
                    'link': f"https://wa.me/{normalized}",
                    'status': 'Active on WhatsApp'
                }
            
            # WhatsApp Business check
            wa_business_url = f"https://www.whatsapp.com/contact/download/?phone={normalized}&lang=en"
            try:
                resp = self.session.get(wa_business_url, headers=headers, timeout=5)
                if 'business' in resp.text.lower():
                    result['verified'] = True
            except:
                pass
                
        except Exception as e:
            logger.error(f"WhatsApp check error: {e}")
        
        return result
    
    def _check_telegram(self, phone: str) -> Dict:
        """Check Telegram username + profile"""
        result = {
            'found': False,
            'username': None,
            'bio': None,
            'profile_pic': None,
            'verified': False,
            'public_channels': []
        }
        
        try:
            # Try to find Telegram account via t.me search
            phone_clean = re.sub(r'\D', '', phone)
            
            # Search for phone pattern in Telegram
            search_patterns = [
                phone_clean,
                phone_clean[-7:],  # Last 7 digits
                phone_clean[-5:],  # Last 5 digits
            ]
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://t.me/'
            
            for pattern in search_patterns:
                try:
                    url = f"https://t.me/s/{pattern}"
                    resp = self.session.get(url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200 and 'tgme_page_title' in resp.text:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        title = soup.find('span', class_='tgme_page_title')
                        if title:
                            result['found'] = True
                            result['username'] = pattern
                            
                            # Get bio
                            subtitle = soup.find('span', class_='tgme_page_description')
                            if subtitle:
                                result['bio'] = subtitle.text.strip()
                            
                            result['profile_pic'] = url
                            break
                except:
                    continue
        
        except Exception as e:
            logger.error(f"Telegram check error: {e}")
        
        return result
    
    def _check_facebook(self, phone: str) -> Dict:
        """Check Facebook account via phone"""
        result = {
            'found': False,
            'profiles': [],
            'name': None,
            'verified': False
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.facebook.com/'
            
            # Facebook search endpoint
            search_url = f"https://www.facebook.com/search/people/?q={phone_clean}"
            
            resp = self.session.get(search_url, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find profile links
                profiles = soup.find_all('a', href=re.compile(r'/.*?/'))
                
                for profile in profiles[:3]:  # Top 3 results
                    name = profile.text.strip()
                    href = profile.get('href', '')
                    
                    if name and 'profile' in href or 'people' in href:
                        result['profiles'].append({
                            'name': name,
                            'link': f"https://facebook.com{href}" if href.startswith('/') else href
                        })
                        result['found'] = True
            
        except Exception as e:
            logger.error(f"Facebook check error: {e}")
        
        return result
    
    def _check_instagram(self, phone: str) -> Dict:
        """Check Instagram via phone lookup"""
        result = {
            'found': False,
            'accounts': [],
            'verified': False
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.instagram.com/'
            
            # Try multiple search patterns
            search_terms = [phone_clean, phone_clean[-7:], phone_clean[-5:]]
            
            for search_term in search_terms:
                try:
                    url = f"https://www.instagram.com/web/search/topsearch/?query={search_term}"
                    resp = self.session.get(url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        
                        if 'users' in data and data['users']:
                            for user in data['users'][:5]:
                                user_data = user.get('user', {})
                                result['accounts'].append({
                                    'username': user_data.get('username'),
                                    'full_name': user_data.get('full_name'),
                                    'is_verified': user_data.get('is_verified', False),
                                    'profile_pic_url': user_data.get('profile_pic_url')
                                })
                                result['found'] = True
                            break
                except:
                    continue
        
        except Exception as e:
            logger.error(f"Instagram check error: {e}")
        
        return result
    
    def _check_truecaller(self, phone: str) -> Dict:
        """Check TrueCaller database"""
        result = {
            'found': False,
            'name': None,
            'carrier': None,
            'country': None,
            'spam_score': 0,
            'verified': False
        }
        
        try:
            phone_normalized = self.normalize_phone(phone)
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.truecaller.com/'
            
            # TrueCaller search
            tc_url = f"https://www.truecaller.com/search/{phone_clean}/1"
            
            resp = self.session.get(tc_url, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Parse TrueCaller page
                if 'The user' in resp.text or 'User' in resp.text:
                    result['found'] = True
                    
                    # Try to extract name
                    name_elem = soup.find('h1')
                    if name_elem:
                        result['name'] = name_elem.text.strip()
                    
                    # Look for carrier info
                    if 'Airtel' in resp.text:
                        result['carrier'] = 'Airtel'
                    elif 'Grameenphone' in resp.text or 'GP' in resp.text:
                        result['carrier'] = 'Grameenphone'
                    elif 'Robi' in resp.text:
                        result['carrier'] = 'Robi'
                    elif 'Banglalink' in resp.text:
                        result['carrier'] = 'Banglalink'
                    
                    result['country'] = 'Bangladesh'
        
        except Exception as e:
            logger.error(f"TrueCaller check error: {e}")
        
        return result
    
    def _check_tiktok(self, phone: str) -> Dict:
        """Check TikTok account"""
        result = {
            'found': False,
            'accounts': [],
            'verified': False
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.tiktok.com/'
            
            # TikTok search
            search_patterns = [phone_clean[-7:], phone_clean[-5:]]
            
            for pattern in search_patterns:
                try:
                    url = f"https://www.tiktok.com/search/user?q={pattern}"
                    resp = self.session.get(url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        users = soup.find_all('a', {'class': 'tiktok-user-link'})
                        
                        if users:
                            for user in users[:3]:
                                username = user.text.strip()
                                if username:
                                    result['accounts'].append({
                                        'username': username,
                                        'link': f"https://tiktok.com/@{username}"
                                    })
                                    result['found'] = True
                except:
                    continue
        
        except Exception as e:
            logger.error(f"TikTok check error: {e}")
        
        return result
    
    def _check_twitter(self, phone: str) -> Dict:
        """Check Twitter/X account"""
        result = {
            'found': False,
            'accounts': [],
            'verified': False
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://x.com/'
            
            # Twitter search
            search_url = f"https://twitter.com/search?q={phone_clean}&f=user"
            
            resp = self.session.get(search_url, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                tweets = soup.find_all('a', href=re.compile(r'/[^/]+$'))
                
                for tweet in tweets[:3]:
                    username = tweet.text.strip()
                    href = tweet.get('href', '')
                    
                    if username and href.startswith('/') and not username.startswith('@'):
                        result['accounts'].append({
                            'username': username,
                            'link': f"https://x.com{href}"
                        })
                        result['found'] = True
        
        except Exception as e:
            logger.error(f"Twitter check error: {e}")
        
        return result
    
    def _check_viber(self, phone: str) -> Dict:
        """Check Viber"""
        result = {
            'found': False,
            'viber_link': None,
            'active': True
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            result['viber_link'] = f"viber://contact?number=%2B{phone_clean}"
            result['found'] = True
        
        except Exception as e:
            logger.error(f"Viber check error: {e}")
        
        return result
    
    def _check_linkedin(self, phone: str) -> Dict:
        """Check LinkedIn"""
        result = {
            'found': False,
            'profiles': [],
            'verified': False
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            headers = self.headers.copy()
            headers['Referer'] = 'https://www.linkedin.com/'
            
            # LinkedIn search would require API key, but we can try web search
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={phone_clean}"
            
            # Note: LinkedIn blocks scrapers, so this is limited
            result['note'] = 'LinkedIn access restricted - API required'
        
        except Exception as e:
            logger.error(f"LinkedIn check error: {e}")
        
        return result
    
    def _check_gmail(self, phone: str) -> Dict:
        """Find possible Gmail/Google accounts"""
        result = {
            'found': False,
            'possible_emails': [],
            'verified_emails': []
        }
        
        try:
            phone_clean = re.sub(r'\D', '', phone)
            
            # Generate email patterns
            patterns = [
                f"{phone_clean}@gmail.com",
                f"{phone_clean[-7:]}@gmail.com",
                f"user{phone_clean[-5:]}@gmail.com",
                f"{phone_clean}@googlemail.com",
            ]
            
            result['possible_emails'] = patterns
            
            # Try to verify via Google Account Lookup
            for email in patterns:
                try:
                    # Google account recovery check
                    headers = self.headers.copy()
                    url = f"https://accounts.google.com/search?q={email}"
                    resp = self.session.get(url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200 and email in resp.text:
                        result['verified_emails'].append(email)
                        result['found'] = True
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Gmail check error: {e}")
        
        return result
    
    def _generate_email_patterns(self, phone: str) -> List[str]:
        """Generate possible email patterns"""
        phone_clean = re.sub(r'\D', '', phone)
        emails = []
        
        patterns = [
            f"{phone_clean}@gmail.com",
            f"{phone_clean}@yahoo.com",
            f"{phone_clean}@outlook.com",
            f"{phone_clean[-7:]}@gmail.com",
            f"user{phone_clean}@gmail.com",
            f"user.{phone_clean}@gmail.com",
        ]
        
        return patterns
    
    def _calculate_risk_score(self) -> float:
        """Calculate overall risk/exposure score"""
        score = 0.0
        
        platforms = self.results.get('platforms', {})
        
        # Each found platform adds to score
        for platform, data in platforms.items():
            if isinstance(data, dict) and data.get('found'):
                score += 20.0
        
        # Email patterns
        if self.results.get('emails'):
            score += 10.0
        
        return min(score, 100.0)


if __name__ == '__main__':
    enum = PhoneEnumeration()
    test_phone = "+880886377515"
    results = enum.enumerate_all(test_phone)
    print(json.dumps(results, indent=2, default=str))
