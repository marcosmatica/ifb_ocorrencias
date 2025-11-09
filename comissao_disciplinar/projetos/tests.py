from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Servidor, Campus, Estudante, Curso, Turma
from .models import Projeto, ParticipacaoServidor, ParticipacaoEstudante
from datetime import timedelta


class ProjetoModelTestCase(TestCase):
    def setUp(self):
        # Criar campus e usuários
        self.campus = Campus.objects.create(nome='Campus Teste', sigla='CT')
        self.user_coord = User.objects.create_user('coord', 'coord@test.com', 'pass')
        self.user_part = User.objects.create_user('part', 'part@test.com', 'pass')

        self.coordenador = Servidor.objects.create(
            user=self.user_coord,
            siape='1234567',
            nome='Coordenador Teste',
            email='coord@test.com',
            campus=self.campus,
            coordenacao='CGEN'
        )

        self.participante = Servidor.objects.create(
            user=self.user_part,
            siape='7654321',
            nome='Participante Teste',
            email='part@test.com',
            campus=self.campus
        )

    def test_criar_projeto(self):
        projeto = Projeto.objects.create(
            numero_processo='23127.000001/2024-00',
            titulo='Projeto Teste',
            data_inicio=timezone.now().date(),
            data_final=timezone.now().date() + timedelta(days=365),
            tema='Teste',
            area='Informática',
            coordenador=self.coordenador,
            criado_por=self.coordenador
        )

        self.assertEqual(projeto.situacao, 'ATIVO')
        self.assertIsNotNone(projeto.proximo_relatorio)

    def test_calculo_proximo_relatorio(self):
        projeto = Projeto.objects.create(
            numero_processo='23127.000002/2024-00',
            titulo='Projeto Teste 2',
            data_inicio=timezone.now().date(),
            data_final=timezone.now().date() + timedelta(days=365),
            tema='Teste',
            area='Informática',
            coordenador=self.coordenador,
            periodicidade_relatorio=6
        )

        projeto.calcular_proximo_relatorio()
        esperado = projeto.data_inicio + timedelta(days=180)

        self.assertEqual(projeto.proximo_relatorio, esperado)

    def test_relatorio_atrasado(self):
        projeto = Projeto.objects.create(
            numero_processo='23127.000003/2024-00',
            titulo='Projeto Atrasado',
            data_inicio=timezone.now().date() - timedelta(days=200),
            data_final=timezone.now().date() + timedelta(days=165),
            tema='Teste',
            area='Informática',
            coordenador=self.coordenador,
            proximo_relatorio=timezone.now().date() - timedelta(days=10)
        )

        self.assertTrue(projeto.relatorio_atrasado())


class ParticipacaoServidorTestCase(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(nome='Campus Teste', sigla='CT')
        self.user = User.objects.create_user('coord', 'coord@test.com', 'pass')

        self.servidor = Servidor.objects.create(
            user=self.user,
            siape='1234567',
            nome='Servidor Teste',
            email='servidor@test.com',
            campus=self.campus
        )

        self.projeto = Projeto.objects.create(
            numero_processo='23127.000001/2024-00',
            titulo='Projeto Teste',
            data_inicio=timezone.now().date(),
            data_final=timezone.now().date() + timedelta(days=365),
            tema='Teste',
            area='Informática',
            coordenador=self.servidor
        )

    def test_limite_horas_semanais(self):
        """Teste se não permite ultrapassar 12h semanais"""
        # Criar participação com 10h
        ParticipacaoServidor.objects.create(
            projeto=self.projeto,
            servidor=self.servidor,
            semestre='2024.1',
            horas_semanais=10
        )

        # Tentar criar segunda participação com 5h (total 15h)
        from django.core.exceptions import ValidationError

        participacao = ParticipacaoServidor(
            projeto=self.projeto,
            servidor=self.servidor,
            semestre='2024.1',
            horas_semanais=5
        )

        with self.assertRaises(ValidationError):
            participacao.full_clean()


class ProjetoViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.campus = Campus.objects.create(nome='Campus Teste', sigla='CT')

        # Criar coordenador de pesquisa/extensão
        self.user_coord_pesq = User.objects.create_user('coordpesq', 'coordpesq@test.com', 'pass')
        self.coord_pesq = Servidor.objects.create(
            user=self.user_coord_pesq,
            siape='1111111',
            nome='Coord Pesquisa',
            email='coordpesq@test.com',
            campus=self.campus,
            coordenacao='CGEN'
        )

        # Criar servidor comum
        self.user_comum = User.objects.create_user('comum', 'comum@test.com', 'pass')
        self.servidor_comum = Servidor.objects.create(
            user=self.user_comum,
            siape='2222222',
            nome='Servidor Comum',
            email='comum@test.com',
            campus=self.campus
        )

        self.projeto = Projeto.objects.create(
            numero_processo='23127.000001/2024-00',
            titulo='Projeto Teste',
            data_inicio=timezone.now().date(),
            data_final=timezone.now().date() + timedelta(days=365),
            tema='Teste',
            area='Informática',
            coordenador=self.coord_pesq
        )

    def test_projeto_list_autenticado(self):
        self.client.login(username='coordpesq', password='pass')
        response = self.client.get('/projetos/')
        self.assertEqual(response.status_code, 200)

    def test_projeto_create_apenas_coord(self):
        # Coordenador de pesquisa pode criar
        self.client.login(username='coordpesq', password='pass')
        response = self.client.get('/projetos/novo/')
        self.assertEqual(response.status_code, 200)

        # Servidor comum não pode
        self.client.login(username='comum', password='pass')
        response = self.client.get('/projetos/novo/')
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_permissoes_visualizacao(self):
        # Coordenador de pesquisa vê tudo
        self.client.login(username='coordpesq', password='pass')
        response = self.client.get(f'/projetos/{self.projeto.pk}/')
        self.assertEqual(response.status_code, 200)

        # Servidor comum não vê projeto que não participa
        self.client.login(username='comum', password='pass')
        response = self.client.get(f'/projetos/{self.projeto.pk}/')
        self.assertEqual(response.status_code, 302)