import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, FROM_EMAIL, EMAIL_PASSWORD, MODERATOR_EMAIL
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def nl2br_email(text, max_length=None):
    """Преобразует переносы строк в HTML теги <br> для email."""
    if not text:
        return ''
    
    text = str(text)
    
    # Заменяем переносы строк
    text = text.replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')
    
    # Обрезаем если нужно
    if max_length and len(text) > max_length:
        text = text[:max_length] + '...'
    
    return text

def send_new_idea_notification(idea):
    """
    Отправляет уведомление о новой идеи модератору.
    """
    server = None
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(FROM_EMAIL, EMAIL_PASSWORD)
        
        # Подготавливаем текст с переносами строк
        essence_preview = nl2br_email(idea.essence[:250], max_length=250)
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.5; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border: 1px solid #ddd; }}
                .header {{ background: #14427a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .idea-card {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #14427a; }}
                .footer {{ text-align: center; padding: 15px; background: #f8f9fa; font-size: 12px; color: #666; }}
                .text-content {{ white-space: pre-line; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Новая идея в системе!</h1>
                    <p>Лаборатория идей РОСТЕСТ</p>
                </div>
                
                <div class="content">
                    <h2>Поступила новая идея для рассмотрения</h2>
                    
                    <div class="idea-card">
                        <h3 style="margin-top: 0;">{idea.title}</h3>
                        
                        <p><strong>📁 Категория:</strong> {idea.category}</p>
                        <p><strong>👤 Автор:</strong> {idea.author_name or 'Аноним'}</p>
                        <p><strong>📅 Дата подачи:</strong> {idea.created_at.strftime('%d.%m.%Y в %H:%M')}</p>
                        <p><strong>🆔 ID идеи:</strong> #{idea.id}</p>
                        
                        <div style="margin: 15px 0;">
                            <strong>💡 Суть предложения:</strong>
                            <div class="text-content" style="background: white; padding: 10px; border-radius: 4px; margin: 8px 0;">
                                {essence_preview}
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #e7f3ff; padding: 15px; border-radius: 4px; border-left: 4px solid #0d6efd;">
                        <strong>💼 Действие:</strong> Пожалуйста, зайдите в систему Лаборатории идей для рассмотрения новой идеи.
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>Лаборатория идей РОСТЕСТ</strong></p>
                    <p>Система автоматических уведомлений</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚀 Новая идея в Лаборатории идей: #{idea.id}"
        msg['From'] = FROM_EMAIL
        msg['To'] = MODERATOR_EMAIL
        
        html_part = MIMEText(html_message, 'html', 'utf-8')
        msg.attach(html_part)
        
        server.sendmail(FROM_EMAIL, MODERATOR_EMAIL, msg.as_string())
        logger.info(f"✅ Уведомление модератору отправлено для идеи #{idea.id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления модератору: {e}")
        return False
        
    finally:
        if server:
            server.quit()

def send_author_confirmation(idea):
    """
    Отправляет подтверждение автору идеи.
    """
    if not idea.contact_email:
        logger.info(f"📭 Email автора не указан для идеи #{idea.id}, пропускаем отправку")
        return True
    
    server = None
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(FROM_EMAIL, EMAIL_PASSWORD)
        
        # Подготавливаем текст с переносами строк
        essence_preview = nl2br_email(idea.essence[:300], max_length=300)
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border: 1px solid #ddd; }}
                .header {{ background: #28a745; color: white; padding: 25px; text-align: center; }}
                .content {{ padding: 25px; }}
                .idea-card {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-left: 4px solid #28a745; border-radius: 4px; }}
                .footer {{ text-align: center; padding: 20px; background: #f8f9fa; font-size: 12px; color: #666; }}
                .status-info {{ background: #d1ecf1; padding: 15px; border-radius: 4px; border-left: 4px solid #0dcaf0; margin: 20px 0; }}
                .text-content {{ white-space: pre-line; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Ваша идея принята!</h1>
                    <p>Лаборатория идей РОСТЕСТ</p>
                </div>
                
                <div class="content">
                    <h2>Спасибо за ваше предложение!</h2>
                    <p>Ваша идея успешно получена и отправлена на модерацию.</p>
                    
                    <div class="idea-card">
                        <h3 style="margin-top: 0; color: #28a745;">{idea.title}</h3>
                        
                        <p><strong>📁 Категория:</strong> {idea.category}</p>
                        <p><strong>👤 Автор:</strong> {idea.author_name or 'Не указано'}</p>
                        <p><strong>📅 Дата подачи:</strong> {idea.created_at.strftime('%d.%m.%Y в %H:%M')}</p>
                        <p><strong>🆔 Номер заявки:</strong> <strong>#{idea.id}</strong></p>
                        
                        <div style="margin: 15px 0;">
                            <strong>💡 Ваше предложение:</strong>
                            <div class="text-content" style="background: white; padding: 12px; border-radius: 4px; margin: 10px 0;">
                                {essence_preview}
                            </div>
                        </div>
                    </div>
                    
                    <div class="status-info">
                        <h4 style="margin-top: 0;">📋 Что дальше?</h4>
                        <ul style="margin-bottom: 0;">
                            <li>Ваша идея будет рассмотрена модератором в ближайшее время</li>
                            <li>При необходимости с вами свяжутся для уточнения деталей</li>
                            <li>Вы получите уведомление об изменении статуса идеи</li>
                        </ul>
                    </div>
                    
                    <div style="background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107;">
                        <strong>💡 Сохраните номер заявки:</strong> #{idea.id} - он может понадобиться для обращения в поддержку.
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>Лаборатория идей РОСТЕСТ</strong></p>
                    <p>Система автоматических уведомлений</p>
                    <p><small>Это письмо отправлено автоматически, пожалуйста, не отвечайте на него.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Ваша идея принята: #{idea.id}"
        msg['From'] = FROM_EMAIL
        msg['To'] = idea.contact_email
        
        html_part = MIMEText(html_message, 'html', 'utf-8')
        msg.attach(html_part)
        
        server.sendmail(FROM_EMAIL, idea.contact_email, msg.as_string())
        logger.info(f"✅ Подтверждение автору отправлено для идеи #{idea.id} на {idea.contact_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки подтверждения автору: {e}")
        return False
        
    finally:
        if server:
            server.quit()

def send_status_update_notification(idea, old_status, new_status):
    """
    Отправляет уведомление автору об изменении статуса идеи.
    """
    if not idea.contact_email:
        logger.info(f"📭 Email автора не указан для идеи #{idea.id}, пропускаем отправку статуса")
        return True
    
    server = None
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(FROM_EMAIL, EMAIL_PASSWORD)
        
        # Определяем цвет и иконку в зависимости от статуса
        status_config = {
            'approved': {'color': '#28a745', 'icon': '✅', 'title': 'Одобрено'},
            'partially_approved': {'color': '#20c997', 'icon': '✅', 'title': 'Одобрено (частично)'},
            'rejected': {'color': '#dc3545', 'icon': '❌', 'title': 'Отклонено'}, 
            'in_progress': {'color': '#0dcaf0', 'icon': '🔄', 'title': 'В работе'},
            'implemented': {'color': '#6f42c1', 'icon': '🎉', 'title': 'Реализовано'}
        }
        
        config = status_config.get(new_status, {'color': '#6c757d', 'icon': '📋', 'title': 'Обновлено'})
        
        # Подготавливаем комментарий модератора с переносами строк
        moderator_feedback_html = ''
        if idea.moderator_feedback:
            feedback_text = nl2br_email(idea.moderator_feedback)
            moderator_feedback_html = f"""
            <div style="margin: 15px 0;">
                <strong>💬 Комментарий модератора:</strong>
                <div class="text-content" style="background: white; padding: 10px; border-radius: 4px; margin: 8px 0;">
                    {feedback_text}
                </div>
            </div>
            """
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border: 1px solid #ddd; }}
                .header {{ background: {config['color']}; color: white; padding: 25px; text-align: center; }}
                .content {{ padding: 25px; }}
                .idea-card {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-left: 4px solid {config['color']}; }}
                .footer {{ text-align: center; padding: 20px; background: #f8f9fa; font-size: 12px; color: #666; }}
                .status-change {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .text-content {{ white-space: pre-line; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{config['icon']} Статус вашей идеи изменен</h1>
                    <p>Лаборатория идей РОСТЕСТ</p>
                </div>
                
                <div class="content">
                    <h2>Статус вашей идеи обновлен</h2>
                    
                    <div class="status-change">
                        <p><strong>Идея:</strong> "{idea.title}"</p>
                        <p><strong>Новый статус:</strong> <span style="color: {config['color']}; font-weight: bold;">{config['title']}</span></p>
                        <p><strong>Номер заявки:</strong> #{idea.id}</p>
                    </div>
                    
                    <div class="idea-card">
                        <h4 style="margin-top: 0;">📋 Детали идеи:</h4>
                        <p><strong>Категория:</strong> {idea.category}</p>
                        <p><strong>Дата подачи:</strong> {idea.created_at.strftime('%d.%m.%Y')}</p>
                        
                        {moderator_feedback_html}
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 4px;">
                        <p><strong>📞 Обратная связь:</strong> Если у вас есть вопросы, вы можете обратиться к модераторам системы.</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>Лаборатория идей РОСТЕСТ</strong></p>
                    <p>Система автоматических уведомлений</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{config['icon']} Статус идеи #{idea.id} изменен: {config['title']}"
        msg['From'] = FROM_EMAIL
        msg['To'] = idea.contact_email
        
        html_part = MIMEText(html_message, 'html', 'utf-8')
        msg.attach(html_part)
        
        server.sendmail(FROM_EMAIL, idea.contact_email, msg.as_string())
        logger.info(f"✅ Уведомление о статусе отправлено автору идеи #{idea.id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления о статусе: {e}")
        return False
        
    finally:
        if server:
            server.quit()