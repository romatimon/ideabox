from alembic import op
import sqlalchemy as sa

def upgrade():
    # Добавляем новое поле для хранения нового статуса
    op.add_column('idea', sa.Column('new_status', sa.String(20)))
    
    # Конвертируем старые статусы в новые
    op.execute("UPDATE idea SET new_status = 'draft' WHERE status = 'Черновик'")
    op.execute("UPDATE idea SET new_status = 'pending' WHERE status = 'На рассмотрении'")
    op.execute("UPDATE idea SET new_status = 'approved' WHERE status = 'Одобрено'")
    op.execute("UPDATE idea SET new_status = 'rejected' WHERE status = 'Отклонено'")
    
    # Удаляем старое поле и переименовываем новое
    op.drop_column('idea', 'status')
    op.alter_column('idea', 'new_status', new_column_name='status')
    
    # Создаем таблицу для логов
    op.create_table('idea_status_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idea_id', sa.Integer(), nullable=True),
        sa.Column('old_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=True),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_id'], ['moderator.id'], ),
        sa.ForeignKeyConstraint(['idea_id'], ['idea.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Обратная миграция (по необходимости)
    pass