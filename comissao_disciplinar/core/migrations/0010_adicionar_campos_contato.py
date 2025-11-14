from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0009_remove_estudante_contato_responsavel_and_more'),
    ]

    operations = [
        # O campo celular já existe em Responsavel, então só precisamos garantir
        # que estudantes tenham responsáveis vinculados
    ]