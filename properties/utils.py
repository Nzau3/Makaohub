"""
Utility functions for the properties app.
"""

import re


def mask_email(email):
    """
    Mask an email address for privacy.
    Shows first 3 characters of username, then ***, then last 2 characters before @, then @domain.
    Example: ndalani62@gmail.com -> nda***62@gmail.com
    """
    if not email or '@' not in email:
        return email

    username, domain = email.split('@', 1)
    if len(username) <= 3:
        masked_username = username
    elif len(username) <= 5:
        # For short usernames, show first 2, then *
        masked_username = username[:2] + '*' * (len(username) - 2)
    else:
        # Show first 3, ***, last 2
        masked_username = username[:3] + '***' + username[-2:]

    return f"{masked_username}@{domain}"


def mask_phone(phone_number):
    """
    Mask a phone number for privacy.
    Shows first 4 digits (or country code + 3 digits for international), then ***, then last 3 digits.
    Example: 0712345678 -> 0712***678
    Example: +254712345678 -> +254712***678
    """
    if not phone_number:
        return phone_number

    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)

    # Find country code if starts with +
    country_code = ''
    if cleaned.startswith('+'):
        # Assume country code is + followed by 1-3 digits
        match = re.match(r'\+(\d{1,3})', cleaned)
        if match:
            country_code = f"+{match.group(1)}"
            remaining = cleaned[len(country_code):]
        else:
            remaining = cleaned[1:]
    else:
        remaining = cleaned

    # Now mask the remaining digits
    if len(remaining) <= 4:
        # Too short, don't mask
        masked = remaining
    else:
        # For international numbers, show first 3, for local show first 4
        if country_code:
            first_show = 3
        else:
            first_show = 4
        
        last_show = 3
        if len(remaining) > first_show + last_show:
            masked = remaining[:first_show] + '***' + remaining[-last_show:]
        else:
            # If not enough, show all but last 3
            masked = remaining[:-3] + '***' + remaining[-3:] if len(remaining) > 3 else remaining

    return f"{country_code}{masked}"


# Example usage
if __name__ == "__main__":
    print(mask_email("john.doe@gmail.com"))  # jo***@gmail.com
    print(mask_email("a@b.com"))  # a*@b.com
    print(mask_email("ab@c.com"))  # ab@c.com
    print(mask_phone("0712345678"))  # 07****678
    print(mask_phone("+254712345678"))  # +2547****678
    print(mask_phone("123"))  # 1**