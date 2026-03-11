"""
╔══════════════════════════════════════════════════════════════╗
║         SISTEMA DE VOTAÇÃO ESCOLAR - URNA ELETRÔNICA         ║
║                  Versão 1.0 — Python + Tkinter               ║
╚══════════════════════════════════════════════════════════════╝

Módulos:
  - GerenciadorDados : leitura e escrita no JSON
  - App              : controlador principal (troca de telas)
  - TelaInicial      : listagem e acesso às eleições
  - TelaCriarEleicao : formulário de nova eleição
  - PainelEleicao    : painel de controle de cada eleição
  - TelaCadastroChapas: gestão das chapas
  - TelaUrna         : interface de votação (estilo urna real)
  - TelaResultados   : apuração e vencedor
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import json
import os
import re
import shutil
import unicodedata
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# ─────────────────────────────────────────────
#  CONSTANTES DE DESIGN
# ─────────────────────────────────────────────
ARQUIVO_JSON    = "eleicoes.json"
PASTA_FOTOS     = "fotos"
SENHA_ADMIN     = "14022004"

# Paleta de cores
COR_FUNDO       = "#0D1117"   # fundo escuro geral
COR_PAINEL      = "#161B22"   # fundo de cards
COR_BORDA       = "#30363D"   # bordas sutis
COR_TEXTO       = "#E6EDF3"   # texto principal
COR_TEXTO2      = "#8B949E"   # texto secundário
COR_VERDE       = "#3FB950"   # confirmação / aberta
COR_VERDE_ESCURO= "#238636"   # botão confirmar
COR_VERMELHO    = "#F85149"   # erro / encerrada
COR_AZUL        = "#388BFD"   # botão primário
COR_AZUL_ESCURO = "#1F6FEB"   # hover botão primário
COR_AMARELO     = "#D29922"   # destaque / vencedor
COR_CINZA       = "#21262D"   # botão secundário
COR_CINZA2      = "#2D333B"   # hover secundário
COR_DISPLAY     = "#010409"   # visor da urna
COR_NUMERO      = "#3FB950"   # dígitos no visor

FONTE_TITULO    = ("Courier New", 22, "bold")
FONTE_SUBTITULO = ("Courier New", 14, "bold")
FONTE_NORMAL    = ("Courier New", 11)
FONTE_PEQUENA   = ("Courier New", 9)
FONTE_DISPLAY   = ("Courier New", 36, "bold")
FONTE_BOTAO_NUM = ("Courier New", 18, "bold")
FONTE_BOTAO     = ("Courier New", 11, "bold")
FONTE_STATUS    = ("Courier New", 10, "bold")


# ════════════════════════════════════════════════════════════════
#  GERENCIADOR DE DADOS  (JSON ↔ memória)
# ════════════════════════════════════════════════════════════════
class GerenciadorDados:
    """
    Responsável por toda leitura e escrita no arquivo JSON.
    Centralizar aqui evita código duplicado nas telas.
    """

    @staticmethod
    def carregar() -> dict:
        """Carrega o JSON ou retorna estrutura vazia se não existir."""
        if not os.path.exists(ARQUIVO_JSON):
            return {"eleicoes": {}}
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
        # Se o arquivo estiver corrompido, começa do zero
            except json.JSONDecodeError:
                return {"eleicoes": {}}

    @staticmethod
    def salvar(dados: dict):
        """Persiste o dicionário inteiro no JSON."""
        with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

    # ─── eleições ───────────────────────────────────────────────
    @staticmethod
    def gerar_chave(nome: str) -> str:
        """
        Gera chave interna a partir do nome:
        'Líder 1º Ano A' → 'lider_1_ano_a'
        Remove acentos, espaços→_, minúsculas.
        """
        nfkd = unicodedata.normalize("NFKD", nome)
        sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
        chave = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento).strip("_").lower()
        return chave or "eleicao"

    @classmethod
    def criar_eleicao(cls, nome: str) -> tuple[bool, str]:
        """
        Cria nova eleição. Retorna (sucesso, mensagem).
        Falha se já existir eleição com o mesmo nome.
        """
        dados = cls.carregar()
        chave = cls.gerar_chave(nome)

        # Verificar duplicata por nome exibido
        for info in dados["eleicoes"].values():
            if info["nome"].strip().lower() == nome.strip().lower():
                return False, "Já existe uma eleição com esse nome."

        # Garantir chave única
        chave_base, contador = chave, 1
        while chave in dados["eleicoes"]:
            chave = f"{chave_base}_{contador}"
            contador += 1

        dados["eleicoes"][chave] = {
            "nome":   nome.strip(),
            "status": "fechada",
            "chapas": {},
            "votos":  {}
        }
        cls.salvar(dados)
        return True, chave

    @classmethod
    def excluir_eleicao(cls, chave: str) -> bool:
        dados = cls.carregar()
        if chave in dados["eleicoes"]:
            del dados["eleicoes"][chave]
            cls.salvar(dados)
            return True
        return False

    # ─── chapas ──────────────────────────────────────────────────
    @classmethod
    def adicionar_chapa(cls, chave_eleicao: str,
                        numero: str, nome1: str, nome2: str,
                        foto1: str = "", foto2: str = "") -> tuple[bool, str]:
        """Cadastra chapa. Número deve ser único dentro da eleição."""
        dados = cls.carregar()
        eleicao = dados["eleicoes"].get(chave_eleicao)
        if not eleicao:
            return False, "Eleição não encontrada."
        if numero in eleicao["chapas"]:
            return False, f"Número {numero} já está em uso."

        # Copiar fotos para a pasta do projeto
        os.makedirs(PASTA_FOTOS, exist_ok=True)
        foto1_salva, foto2_salva = "", ""
        if foto1 and os.path.isfile(foto1):
            ext = os.path.splitext(foto1)[1]
            foto1_salva = os.path.join(PASTA_FOTOS, f"{chave_eleicao}_{numero}_1{ext}")
            shutil.copy2(foto1, foto1_salva)
        if foto2 and os.path.isfile(foto2):
            ext = os.path.splitext(foto2)[1]
            foto2_salva = os.path.join(PASTA_FOTOS, f"{chave_eleicao}_{numero}_2{ext}")
            shutil.copy2(foto2, foto2_salva)

        eleicao["chapas"][numero] = {
            "nomes": [nome1.strip(), nome2.strip()],
            "fotos": [foto1_salva, foto2_salva]
        }
        cls.salvar(dados)
        return True, "Chapa cadastrada com sucesso."

    @classmethod
    def remover_chapa(cls, chave_eleicao: str, numero: str) -> bool:
        dados = cls.carregar()
        chapas = dados["eleicoes"][chave_eleicao]["chapas"]
        if numero in chapas:
            info = chapas[numero]
            # Remove arquivos de foto
            fotos = info.get("fotos", []) if isinstance(info, dict) else []
            for f in fotos:
                if f and os.path.isfile(f):
                    os.remove(f)
            del chapas[numero]
            dados["eleicoes"][chave_eleicao]["votos"].pop(numero, None)
            cls.salvar(dados)
            return True
        return False

    # ─── votação ─────────────────────────────────────────────────
    @classmethod
    def registrar_voto(cls, chave_eleicao: str, numero_chapa: str) -> tuple[bool, str]:
        """Registra voto se eleição estiver aberta e chapa existir."""
        dados = cls.carregar()
        eleicao = dados["eleicoes"].get(chave_eleicao)
        if not eleicao:
            return False, "Eleição inválida."
        if eleicao["status"] != "aberta":
            return False, "Votação não está aberta."
        if numero_chapa not in eleicao["chapas"]:
            return False, "Chapa não encontrada."

        votos = eleicao.setdefault("votos", {})
        votos[numero_chapa] = votos.get(numero_chapa, 0) + 1
        cls.salvar(dados)
        return True, "Voto registrado."

    # ─── controle de status ──────────────────────────────────────
    @classmethod
    def set_status(cls, chave_eleicao: str, status: str):
        dados = cls.carregar()
        dados["eleicoes"][chave_eleicao]["status"] = status
        cls.salvar(dados)

    # ─── consultas ───────────────────────────────────────────────
    @classmethod
    def obter_eleicao(cls, chave: str) -> dict | None:
        return cls.carregar()["eleicoes"].get(chave)

    @classmethod
    def listar_eleicoes(cls) -> dict:
        return cls.carregar()["eleicoes"]


# ─── helpers de dados de chapa ──────────────────────────────────
def _chapa_nomes(info) -> list[str]:
    """Extrai [nome1, nome2] de uma chapa (formato antigo ou novo)."""
    if isinstance(info, dict):
        return info.get("nomes", ["", ""])
    return info   # formato antigo: [nome1, nome2]


def _chapa_fotos(info) -> list[str]:
    """Extrai [foto1, foto2] de uma chapa."""
    if isinstance(info, dict):
        return info.get("fotos", ["", ""])
    return ["", ""]


def _carregar_foto(caminho: str, tamanho: tuple[int, int] = (80, 80)):
    """Carrega e redimensiona uma foto. Retorna ImageTk.PhotoImage ou None."""
    if Image is None or ImageTk is None:
        return None
    if not caminho or not os.path.isfile(caminho):
        return None
    try:
        img = Image.open(caminho)
        img = img.resize(tamanho, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════
#  HELPERS DE UI
# ════════════════════════════════════════════════════════════════
def btn(parent, texto, comando, cor=COR_AZUL, largura=22, altura=2, fonte=FONTE_BOTAO):
    """Fábrica de botões com estilo padrão."""
    b = tk.Button(
        parent, text=texto, command=comando,
        bg=cor, fg=COR_TEXTO, font=fonte,
        width=largura, height=altura,
        relief="flat", cursor="hand2",
        activebackground=COR_AZUL_ESCURO, activeforeground=COR_TEXTO,
        bd=0, padx=8
    )
    return b


def label(parent, texto, fonte=FONTE_NORMAL, cor=COR_TEXTO, ancora="w"):
    return tk.Label(parent, text=texto, font=fonte, fg=cor,
                    bg=COR_FUNDO, anchor=ancora)


def separador(parent, cor=COR_BORDA):
    return tk.Frame(parent, height=1, bg=cor)


def card(parent, pad=16):
    """Frame com visual de cartão."""
    f = tk.Frame(parent, bg=COR_PAINEL, bd=0,
                 highlightbackground=COR_BORDA, highlightthickness=1)
    return f


def rodape(parent):
    """Rodapé padrão com créditos."""
    tk.Label(parent, text="Desenvolvido em 1 dia por Esly Caetano 🥸",
             font=FONTE_PEQUENA, fg=COR_TEXTO2, bg=COR_FUNDO
             ).pack(side="bottom", pady=6)


# ════════════════════════════════════════════════════════════════
#  APP  — controlador principal
# ════════════════════════════════════════════════════════════════
class App:
    """
    Gerencia a janela principal e a troca de 'páginas' (Frames).
    Cada tela é instanciada como um Frame e empilhada; apenas a
    ativa fica visível (pack/pack_forget).
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Urna Escolar — Sistema de Votação")
        self.root.geometry("900x680")
        self.root.minsize(800, 600)
        self.root.configure(bg=COR_FUNDO)

        # Centraliza a janela na tela
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 900) // 2
        y = (self.root.winfo_screenheight() - 680) // 2
        self.root.geometry(f"900x680+{x}+{y}")

        self._tela_atual = None
        self.ir_para_tela_inicial()

    # ─── navegação ──────────────────────────────────────────────
    def _trocar_tela(self, nova_tela_cls, **kwargs):
        """Destrói a tela atual e instancia a nova."""
        if self._tela_atual:
            self._tela_atual.destroy()
        self._tela_atual = nova_tela_cls(self.root, self, **kwargs)
        self._tela_atual.pack(fill="both", expand=True)

    def ir_para_tela_inicial(self):
        self._trocar_tela(TelaInicial)

    def ir_para_criar_eleicao(self):
        self._trocar_tela(TelaCriarEleicao)

    def ir_para_painel(self, chave_eleicao: str):
        self._trocar_tela(PainelEleicao, chave=chave_eleicao)

    def ir_para_chapas(self, chave_eleicao: str):
        self._trocar_tela(TelaCadastroChapas, chave=chave_eleicao)

    def ir_para_urna(self, chave_eleicao: str):
        self._trocar_tela(TelaUrna, chave=chave_eleicao)

    def ir_para_resultados(self, chave_eleicao: str):
        self._trocar_tela(TelaResultados, chave=chave_eleicao)

    def executar(self):
        self.root.mainloop()


# ════════════════════════════════════════════════════════════════
#  TELA INICIAL
# ════════════════════════════════════════════════════════════════
class TelaInicial(tk.Frame):
    """
    Página principal: lista eleições existentes e oferece
    ações para criar, gerenciar ou sair.
    """

    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COR_FUNDO)
        self.app = app
        self._construir()

    def _construir(self):
        # ── Cabeçalho ──────────────────────────────────────────
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x", padx=0, pady=0)

        tk.Label(cab, text="🗳  URNA ESCOLAR",
                 font=FONTE_TITULO, fg=COR_VERDE, bg=COR_PAINEL
                 ).pack(pady=(18, 2))

        tk.Label(cab, text="Sistema de Votação — Eleições de Turma",
                 font=FONTE_PEQUENA, fg=COR_TEXTO2, bg=COR_PAINEL
                 ).pack(pady=(0, 14))

        # ── Corpo ───────────────────────────────────────────────
        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=24, pady=16)

        # Coluna esquerda: lista de eleições
        esq = tk.Frame(corpo, bg=COR_FUNDO)
        esq.pack(side="left", fill="both", expand=True, padx=(0, 16))

        tk.Label(esq, text="ELEIÇÕES CADASTRADAS",
                 font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_FUNDO
                 ).pack(anchor="w", pady=(0, 8))

        separador(esq).pack(fill="x", pady=4)

        # Frame com scroll para a lista
        container = tk.Frame(esq, bg=COR_FUNDO)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=COR_FUNDO, highlightthickness=0)
        scroll = tk.Scrollbar(container, orient="vertical",
                               command=canvas.yview)
        self.lista_frame = tk.Frame(canvas, bg=COR_FUNDO)

        self.lista_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.lista_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._popular_lista()

        # Coluna direita: botões de ação
        dir_ = tk.Frame(corpo, bg=COR_FUNDO, width=220)
        dir_.pack(side="right", fill="y", padx=(16, 0))
        dir_.pack_propagate(False)

        tk.Label(dir_, text="AÇÕES",
                 font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_FUNDO
                 ).pack(anchor="w", pady=(0, 8))

        separador(dir_).pack(fill="x", pady=4)

        btn(dir_, "＋  Nova Eleição",
            self.app.ir_para_criar_eleicao,
            cor=COR_VERDE_ESCURO, largura=24
            ).pack(pady=6, fill="x")

        btn(dir_, "✖  Sair",
            self.app.root.quit,
            cor="#6E0D0D", largura=24
            ).pack(pady=6, fill="x")

        # Rodapé
        rodape(self)

    def _popular_lista(self):
        """Preenche a lista de eleições com botões clicáveis."""
        for w in self.lista_frame.winfo_children():
            w.destroy()

        eleicoes = GerenciadorDados.listar_eleicoes()

        if not eleicoes:
            tk.Label(self.lista_frame,
                     text="Nenhuma eleição cadastrada ainda.\n"
                          "Clique em 'Nova Eleição' para começar.",
                     font=FONTE_NORMAL, fg=COR_TEXTO2, bg=COR_FUNDO,
                     justify="center"
                     ).pack(pady=40)
            return

        for chave, info in eleicoes.items():
            self._criar_item_eleicao(chave, info)

    def _criar_item_eleicao(self, chave: str, info: dict):
        """Cria um item (card) na lista de eleições."""
        status = info.get("status", "fechada")
        cor_status = COR_VERDE if status == "aberta" else COR_VERMELHO
        icone = "🟢" if status == "aberta" else "🔴"

        item = tk.Frame(self.lista_frame, bg=COR_PAINEL, cursor="hand2",
                        highlightbackground=COR_BORDA, highlightthickness=1)
        item.pack(fill="x", pady=4, ipady=6)

        tk.Label(item, text=icone + "  " + info["nome"],
                 font=FONTE_SUBTITULO, fg=COR_TEXTO, bg=COR_PAINEL,
                 anchor="w"
                 ).pack(side="left", padx=12, pady=4)

        tk.Label(item, text=status.upper(),
                 font=FONTE_STATUS, fg=cor_status, bg=COR_PAINEL
                 ).pack(side="right", padx=12)

        total_chapas = len(info.get("chapas", {}))
        total_votos  = sum(info.get("votos", {}).values())
        tk.Label(item,
                 text=f"{total_chapas} chapa(s) · {total_votos} voto(s)",
                 font=FONTE_PEQUENA, fg=COR_TEXTO2, bg=COR_PAINEL
                 ).pack(side="right", padx=8)

        # Toda a linha é clicável
        def _on_enter(e, frame=item):
            frame.configure(bg=COR_CINZA2)
            for child in frame.winfo_children():
                child.configure(bg=COR_CINZA2)

        def _on_leave(e, frame=item):
            frame.configure(bg=COR_PAINEL)
            for child in frame.winfo_children():
                child.configure(bg=COR_PAINEL)

        for w in [item] + item.winfo_children():
            w.bind("<Button-1>",
                   lambda e, k=chave: self.app.ir_para_painel(k))
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)


# ════════════════════════════════════════════════════════════════
#  TELA CRIAR ELEIÇÃO
# ════════════════════════════════════════════════════════════════
class TelaCriarEleicao(tk.Frame):
    """Formulário simples para criação de nova eleição."""

    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COR_FUNDO)
        self.app = app
        rodape(self)
        self._construir()

    def _construir(self):
        self._cabecalho("CRIAR NOVA ELEIÇÃO")

        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=40, pady=20)

        c = card(corpo)
        c.pack(fill="x", pady=8, ipady=12)

        tk.Label(c, text="Nome da Eleição", font=FONTE_SUBTITULO,
                 fg=COR_TEXTO, bg=COR_PAINEL
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(c, text='Ex: "Líder de Turma 1º Ano A" ou "Grêmio Estudantil"',
                 font=FONTE_PEQUENA, fg=COR_TEXTO2, bg=COR_PAINEL
                 ).pack(anchor="w", padx=16, pady=(0, 8))

        self.entry_nome = tk.Entry(
            c, font=FONTE_NORMAL, bg=COR_DISPLAY, fg=COR_NUMERO,
            insertbackground=COR_NUMERO, relief="flat",
            highlightbackground=COR_VERDE, highlightthickness=1,
            width=42
        )
        self.entry_nome.pack(padx=16, pady=(0, 12), ipady=8)
        self.entry_nome.bind("<Return>", lambda e: self._criar())

        separador(corpo).pack(fill="x", pady=12)

        linha = tk.Frame(corpo, bg=COR_FUNDO)
        linha.pack()

        btn(linha, "✔  Criar Eleição", self._criar,
            cor=COR_VERDE_ESCURO, largura=20).pack(side="left", padx=6)
        btn(linha, "← Voltar", self.app.ir_para_tela_inicial,
            cor=COR_CINZA, largura=16).pack(side="left", padx=6)

        self.lbl_msg = tk.Label(corpo, text="", font=FONTE_NORMAL,
                                fg=COR_VERMELHO, bg=COR_FUNDO)
        self.lbl_msg.pack(pady=8)

    def _cabecalho(self, titulo: str):
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x")
        tk.Label(cab, text=titulo, font=FONTE_TITULO,
                 fg=COR_VERDE, bg=COR_PAINEL
                 ).pack(pady=18)

    def _criar(self):
        nome = self.entry_nome.get().strip()
        if not nome:
            self.lbl_msg.config(text="⚠  O nome da eleição não pode ser vazio.",
                                fg=COR_AMARELO)
            return

        ok, resultado = GerenciadorDados.criar_eleicao(nome)
        if ok:
            messagebox.showinfo("Eleição Criada",
                                f'Eleição "{nome}" criada com sucesso!')
            self.app.ir_para_painel(resultado)
        else:
            self.lbl_msg.config(text=f"⚠  {resultado}", fg=COR_VERMELHO)


# ════════════════════════════════════════════════════════════════
#  PAINEL DA ELEIÇÃO
# ════════════════════════════════════════════════════════════════
class PainelEleicao(tk.Frame):
    """
    Hub de controle de uma eleição específica.
    Mostra status e oferece acesso a todas as funcionalidades.
    """

    def __init__(self, parent, app: App, chave: str):
        super().__init__(parent, bg=COR_FUNDO)
        self.app   = app
        self.chave = chave
        rodape(self)
        self._construir()

    def _construir(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        if not eleicao:
            tk.Label(self, text="Eleição não encontrada.",
                     font=FONTE_SUBTITULO, fg=COR_VERMELHO, bg=COR_FUNDO
                     ).pack(pady=40)
            btn(self, "← Voltar", self.app.ir_para_tela_inicial,
                cor=COR_CINZA).pack()
            return

        status = eleicao.get("status", "fechada")
        cor_s  = COR_VERDE if status == "aberta" else COR_VERMELHO

        # ── Cabeçalho ──────────────────────────────────────────
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x")

        tk.Label(cab, text="🗳  " + eleicao["nome"],
                 font=FONTE_TITULO, fg=COR_VERDE, bg=COR_PAINEL
                 ).pack(pady=(18, 2))

        tk.Label(cab, text=f"STATUS: {status.upper()}",
                 font=FONTE_STATUS, fg=cor_s, bg=COR_PAINEL
                 ).pack(pady=(0, 14))

        # ── Estatísticas rápidas ────────────────────────────────
        stats = tk.Frame(self, bg=COR_FUNDO)
        stats.pack(padx=24, pady=12)

        total_chapas = len(eleicao.get("chapas", {}))
        total_votos  = sum(eleicao.get("votos",  {}).values())

        for titulo, valor, cor in [
            ("Chapas",    str(total_chapas), COR_AZUL),
            ("Votos",     str(total_votos),  COR_AMARELO),
            ("Status",    status.capitalize(), cor_s),
        ]:
            f = card(stats)
            f.pack(side="left", padx=8, ipadx=16, ipady=8)
            tk.Label(f, text=valor, font=("Courier New", 28, "bold"),
                     fg=cor, bg=COR_PAINEL).pack()
            tk.Label(f, text=titulo, font=FONTE_PEQUENA,
                     fg=COR_TEXTO2, bg=COR_PAINEL).pack()

        separador(self).pack(fill="x", padx=24, pady=4)

        # ── Botões de ação ──────────────────────────────────────
        acoes = tk.Frame(self, bg=COR_FUNDO)
        acoes.pack(fill="both", expand=True, padx=24, pady=8)

        # Linha 1
        l1 = tk.Frame(acoes, bg=COR_FUNDO)
        l1.pack(pady=6)

        btn(l1, "📋  Cadastrar Chapas",
            lambda: self.app.ir_para_chapas(self.chave),
            cor=COR_AZUL, largura=22
            ).pack(side="left", padx=8)

        btn(l1, "📊  Ver Resultados",
            self._ver_resultados,
            cor=COR_AMARELO, largura=22
            ).pack(side="left", padx=8)

        # Linha 2
        l2 = tk.Frame(acoes, bg=COR_FUNDO)
        l2.pack(pady=6)

        if status == "fechada":
            btn(l2, "▶  Iniciar Votação",
                self._iniciar_votacao,
                cor=COR_VERDE_ESCURO, largura=22
                ).pack(side="left", padx=8)
        else:
            btn(l2, "⬛  Encerrar Votação",
                self._encerrar_votacao,
                cor=COR_VERMELHO, largura=22
                ).pack(side="left", padx=8)

        btn(l2, "🗳  Abrir Urna",
            lambda: self.app.ir_para_urna(self.chave),
            cor="#8957e5", largura=22
            ).pack(side="left", padx=8)

        # Linha 3
        l3 = tk.Frame(acoes, bg=COR_FUNDO)
        l3.pack(pady=6)

        btn(l3, "🗑  Excluir Eleição",
            self._excluir_eleicao,
            cor="#6E0D0D", largura=22
            ).pack(side="left", padx=8)

        btn(l3, "← Voltar",
            self.app.ir_para_tela_inicial,
            cor=COR_CINZA, largura=22
            ).pack(side="left", padx=8)

    # ─── ações ─────────────────────────────────────────────────
    def _ver_resultados(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        if eleicao.get("status") == "aberta":
            messagebox.showwarning("Atenção",
                "Encerre a votação antes de ver os resultados.")
            return
        self.app.ir_para_resultados(self.chave)

    def _iniciar_votacao(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        if not eleicao.get("chapas"):
            messagebox.showwarning("Atenção",
                "Cadastre ao menos uma chapa antes de iniciar a votação.")
            return
        if messagebox.askyesno("Iniciar Votação",
                               "Confirma abertura da votação?"):
            GerenciadorDados.set_status(self.chave, "aberta")
            self._reconstruir()

    def _encerrar_votacao(self):
        senha = simpledialog.askstring(
            "Senha do Administrador",
            "Digite a senha para encerrar a votação:",
            show="*", parent=self
        )
        if senha is None:
            return
        if senha != SENHA_ADMIN:
            messagebox.showerror("Acesso Negado", "Senha incorreta.")
            return
        GerenciadorDados.set_status(self.chave, "fechada")
        messagebox.showinfo("Votação Encerrada",
                            "A votação foi encerrada com sucesso.")
        self._reconstruir()

    def _excluir_eleicao(self):
        if messagebox.askyesno("Excluir Eleição",
                               "Tem certeza? Todos os dados serão apagados.",
                               icon="warning"):
            GerenciadorDados.excluir_eleicao(self.chave)
            self.app.ir_para_tela_inicial()

    def _reconstruir(self):
        """Recarrega a tela após mudança de estado."""
        self.app.ir_para_painel(self.chave)


# ════════════════════════════════════════════════════════════════
#  TELA CADASTRO DE CHAPAS
# ════════════════════════════════════════════════════════════════
class TelaCadastroChapas(tk.Frame):
    """
    Permite cadastrar e remover chapas de uma eleição.
    Campos: número, nome do 1º integrante, nome do 2º integrante.
    """

    def __init__(self, parent, app: App, chave: str):
        super().__init__(parent, bg=COR_FUNDO)
        self.app   = app
        self.chave = chave
        rodape(self)
        self._construir()

    def _construir(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)

        # ── Cabeçalho ──────────────────────────────────────────
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x")
        tk.Label(cab, text="📋  CADASTRO DE CHAPAS — " + eleicao["nome"],
                 font=FONTE_SUBTITULO, fg=COR_VERDE, bg=COR_PAINEL
                 ).pack(pady=14)

        btn(cab, "← Painel", lambda: self.app.ir_para_painel(self.chave),
            cor=COR_CINZA, largura=14, altura=1
            ).pack(side="right", padx=16, pady=10)

        # ── Corpo ───────────────────────────────────────────────
        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=24, pady=12)

        # Formulário de cadastro
        form = card(corpo)
        form.pack(fill="x", pady=8, ipady=8)

        tk.Label(form, text="NOVA CHAPA",
                 font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_PAINEL
                 ).pack(anchor="w", padx=16, pady=(10, 6))

        linha_form = tk.Frame(form, bg=COR_PAINEL)
        linha_form.pack(fill="x", padx=16, pady=(0, 12))

        def campo(parent, label_txt, largura=18):
            f = tk.Frame(parent, bg=COR_PAINEL)
            f.pack(side="left", padx=4)
            tk.Label(f, text=label_txt, font=FONTE_PEQUENA,
                     fg=COR_TEXTO2, bg=COR_PAINEL
                     ).pack(anchor="w")
            e = tk.Entry(f, font=FONTE_NORMAL, bg=COR_DISPLAY,
                         fg=COR_NUMERO, insertbackground=COR_NUMERO,
                         relief="flat", highlightbackground=COR_VERDE,
                         highlightthickness=1, width=largura)
            e.pack(ipady=6)
            return e

        self.e_num   = campo(linha_form, "Número (ex: 10)", largura=10)
        self.e_nome1 = campo(linha_form, "Líder",          largura=22)
        self.e_nome2 = campo(linha_form, "Vice-Líder",      largura=22)

        # Botões de foto
        self._foto1_path = ""
        self._foto2_path = ""
        f_fotos = tk.Frame(linha_form, bg=COR_PAINEL)
        f_fotos.pack(side="left", padx=4)
        tk.Label(f_fotos, text="Fotos", font=FONTE_PEQUENA,
                 fg=COR_TEXTO2, bg=COR_PAINEL).pack(anchor="w")
        linha_fotos = tk.Frame(f_fotos, bg=COR_PAINEL)
        linha_fotos.pack()
        self.btn_foto1 = tk.Button(
            linha_fotos, text="📷 Líder", font=FONTE_PEQUENA,
            bg=COR_CINZA, fg=COR_TEXTO, relief="flat", cursor="hand2",
            activebackground=COR_CINZA2,
            command=lambda: self._selecionar_foto(1)
        )
        self.btn_foto1.pack(side="left", padx=2, ipady=6)
        self.btn_foto2 = tk.Button(
            linha_fotos, text="📷 Vice-Líder", font=FONTE_PEQUENA,
            bg=COR_CINZA, fg=COR_TEXTO, relief="flat", cursor="hand2",
            activebackground=COR_CINZA2,
            command=lambda: self._selecionar_foto(2)
        )
        self.btn_foto2.pack(side="left", padx=2, ipady=6)

        btn(linha_form, "＋ Adicionar", self._adicionar,
            cor=COR_VERDE_ESCURO, largura=14, altura=1
            ).pack(side="left", padx=(12, 0), pady=(16, 0))

        self.lbl_erro = tk.Label(form, text="", font=FONTE_NORMAL,
                                  fg=COR_VERMELHO, bg=COR_PAINEL)
        self.lbl_erro.pack(anchor="w", padx=16, pady=(0, 4))

        separador(corpo).pack(fill="x", pady=8)

        # Lista de chapas
        tk.Label(corpo, text="CHAPAS CADASTRADAS",
                 font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_FUNDO
                 ).pack(anchor="w")

        self.lista_frame = tk.Frame(corpo, bg=COR_FUNDO)
        self.lista_frame.pack(fill="both", expand=True, pady=8)

        self._popular_lista()

    def _popular_lista(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()

        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        chapas  = eleicao.get("chapas", {})

        if not chapas:
            tk.Label(self.lista_frame,
                     text="Nenhuma chapa cadastrada ainda.",
                     font=FONTE_NORMAL, fg=COR_TEXTO2, bg=COR_FUNDO
                     ).pack(pady=20)
            return

        # Cabeçalho da tabela
        cab = tk.Frame(self.lista_frame, bg=COR_CINZA)
        cab.pack(fill="x", pady=2)
        for txt, l in [("Nº", 6), ("Líder", 24), ("Vice-Líder", 24), ("", 10)]:
            tk.Label(cab, text=txt, font=FONTE_BOTAO, fg=COR_TEXTO2,
                     bg=COR_CINZA, width=l, anchor="w"
                     ).pack(side="left", padx=8, pady=4)

        for numero, info in sorted(chapas.items(), key=lambda x: int(x[0])):
            nomes = _chapa_nomes(info)
            linha = tk.Frame(self.lista_frame, bg=COR_PAINEL,
                             highlightbackground=COR_BORDA,
                             highlightthickness=1)
            linha.pack(fill="x", pady=2)

            tk.Label(linha, text=numero, font=FONTE_NORMAL,
                     fg=COR_AMARELO, bg=COR_PAINEL, width=6, anchor="w"
                     ).pack(side="left", padx=8, pady=6)

            # Miniaturas de foto
            fotos = _chapa_fotos(info)
            for foto_path in fotos:
                img = _carregar_foto(foto_path, (32, 32))
                if img:
                    lbl_img = tk.Label(linha, image=img, bg=COR_PAINEL)
                    lbl_img.image = img  # manter referência
                    lbl_img.pack(side="left", padx=2)
                else:
                    tk.Label(linha, text="\u2014", font=FONTE_PEQUENA,
                             fg=COR_TEXTO2, bg=COR_PAINEL, width=4
                             ).pack(side="left", padx=2)

            tk.Label(linha, text=nomes[0], font=FONTE_NORMAL,
                     fg=COR_TEXTO, bg=COR_PAINEL, width=20, anchor="w"
                     ).pack(side="left", padx=4)
            tk.Label(linha, text=nomes[1], font=FONTE_NORMAL,
                     fg=COR_TEXTO, bg=COR_PAINEL, width=20, anchor="w"
                     ).pack(side="left", padx=4)

            btn(linha, "Remover",
                lambda n=numero: self._remover(n),
                cor=COR_VERMELHO, largura=10, altura=1
                ).pack(side="right", padx=8, pady=4)

    def _adicionar(self):
        numero = self.e_num.get().strip()
        nome1  = self.e_nome1.get().strip()
        nome2  = self.e_nome2.get().strip()

        # Validações básicas
        if not numero or not nome1 or not nome2:
            self.lbl_erro.config(text="⚠  Preencha todos os campos.")
            return
        if not numero.isdigit():
            self.lbl_erro.config(text="⚠  O número da chapa deve conter apenas dígitos.")
            return

        ok, msg = GerenciadorDados.adicionar_chapa(
            self.chave, numero, nome1, nome2,
            self._foto1_path, self._foto2_path
        )
        if ok:
            self.lbl_erro.config(text="")
            self.e_num.delete(0, "end")
            self.e_nome1.delete(0, "end")
            self.e_nome2.delete(0, "end")
            self._foto1_path = ""
            self._foto2_path = ""
            self.btn_foto1.config(text="📷 Líder", bg=COR_CINZA)
            self.btn_foto2.config(text="📷 Vice-Líder", bg=COR_CINZA)
            self._popular_lista()
        else:
            self.lbl_erro.config(text=f"⚠  {msg}")

    def _remover(self, numero: str):
        if messagebox.askyesno("Remover Chapa",
                               f"Remover chapa {numero}? Os votos dela também serão apagados."):
            GerenciadorDados.remover_chapa(self.chave, numero)
            self._popular_lista()

    def _selecionar_foto(self, integrante: int):
        """Abre diálogo para selecionar foto do Líder ou Vice-Líder."""
        cargo = "Líder" if integrante == 1 else "Vice-Líder"
        caminho = filedialog.askopenfilename(
            title=f"Selecionar foto — {cargo}",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif")],
            parent=self
        )
        if not caminho:
            return
        if integrante == 1:
            self._foto1_path = caminho
            self.btn_foto1.config(text="✔ Líder", bg=COR_VERDE_ESCURO)
        else:
            self._foto2_path = caminho
            self.btn_foto2.config(text="✔ Vice-Líder", bg=COR_VERDE_ESCURO)


# ════════════════════════════════════════════════════════════════
#  TELA DA URNA  (interface estilo urna real)
# ════════════════════════════════════════════════════════════════
class TelaUrna(tk.Frame):
    """
    Simula uma urna eletrônica real:
    - Visor digital com número digitado
    - Teclado numérico 0–9
    - Botões CORRIGIR e CONFIRMAR
    - Exibe nome da chapa ao digitar número válido
    - Mensagem de erro se número não existir
    - Bloqueada se eleição estiver fechada
    """

    MAX_DIGITOS = 2   # chapas de 2 dígitos por padrão

    def __init__(self, parent, app: App, chave: str):
        super().__init__(parent, bg=COR_FUNDO)
        self.app     = app
        self.chave   = chave
        self.digitos   = ""          # dígitos digitados até agora
        self.estado    = "digitando" # 'digitando' | 'confirmado' | 'erro'
        self._after_id = None        # ID do callback agendado
        rodape(self)
        self._construir()

    def _construir(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)

        # ── Cabeçalho ──────────────────────────────────────────
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x")
        tk.Label(cab, text="🗳  URNA ELETRÔNICA — " + eleicao["nome"],
                 font=FONTE_SUBTITULO, fg=COR_VERDE, bg=COR_PAINEL
                 ).pack(pady=12)

        btn(cab, "← Painel", lambda: self.app.ir_para_painel(self.chave),
            cor=COR_CINZA, largura=12, altura=1
            ).pack(side="right", padx=16, pady=10)

        # ── Bloquear se fechada ─────────────────────────────────
        if eleicao.get("status") != "aberta":
            tk.Label(self,
                     text="⛔  VOTAÇÃO ENCERRADA\n\n"
                          "Inicie a votação no painel antes de usar a urna.",
                     font=FONTE_SUBTITULO, fg=COR_VERMELHO, bg=COR_FUNDO,
                     justify="center"
                     ).pack(expand=True)
            return

        # ── Determinar tamanho máximo de dígitos ─────────────────
        chapas = eleicao.get("chapas", {})
        if chapas:
            max_num = max(len(n) for n in chapas.keys())
            self.MAX_DIGITOS = max_num

        # ── Layout horizontal: esquerda=urna, direita=info ─────
        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(expand=True, pady=12)

        # ── Lado esquerdo: visor + teclado ──
        esq = tk.Frame(corpo, bg=COR_FUNDO)
        esq.pack(side="left", padx=(0, 24))

        tk.Label(esq,
                 text="DIGITE O NÚMERO DA CHAPA",
                 font=("Courier New", 12, "bold"),
                 fg=COR_TEXTO2, bg=COR_FUNDO
                 ).pack(pady=(0, 8))

        visor_frame = tk.Frame(esq, bg=COR_DISPLAY,
                               highlightbackground=COR_VERDE,
                               highlightthickness=2)
        visor_frame.pack(pady=4)

        self.lbl_display = tk.Label(
            visor_frame,
            text="",
            font=FONTE_DISPLAY,
            fg=COR_NUMERO, bg=COR_DISPLAY,
            width=8, height=2,
            anchor="center"
        )
        self.lbl_display.pack(padx=20, pady=10)

        teclado = tk.Frame(esq, bg=COR_FUNDO)
        teclado.pack(pady=8)

        layout = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["",  "0", ""],
        ]

        for linha in layout:
            fr = tk.Frame(teclado, bg=COR_FUNDO)
            fr.pack()
            for digito in linha:
                if digito == "":
                    tk.Frame(fr, width=72, height=72, bg=COR_FUNDO
                             ).pack(side="left", padx=4, pady=4)
                else:
                    b = tk.Button(
                        fr, text=digito,
                        font=FONTE_BOTAO_NUM,
                        bg=COR_CINZA, fg=COR_TEXTO,
                        width=4, height=2,
                        relief="flat", cursor="hand2",
                        activebackground=COR_CINZA2,
                        command=lambda d=digito: self._digitar(d)
                    )
                    b.pack(side="left", padx=4, pady=4)

        linha_btn = tk.Frame(esq, bg=COR_FUNDO)
        linha_btn.pack(pady=10)

        tk.Button(
            linha_btn, text="CORRIGIR",
            font=FONTE_BOTAO, bg=COR_AMARELO, fg=COR_FUNDO,
            width=14, height=2, relief="flat", cursor="hand2",
            activebackground="#b07e00",
            command=self._corrigir
        ).pack(side="left", padx=10)

        tk.Button(
            linha_btn, text="CONFIRMAR",
            font=FONTE_BOTAO, bg=COR_VERDE_ESCURO, fg=COR_TEXTO,
            width=14, height=2, relief="flat", cursor="hand2",
            activebackground="#1a6e2a",
            command=self._confirmar
        ).pack(side="left", padx=10)

        # ── Lado direito: info da chapa ──
        self._fotos_refs = []

        self.painel_dir = tk.Frame(corpo, bg=COR_PAINEL, width=280,
                                   highlightbackground=COR_BORDA,
                                   highlightthickness=1)
        self.painel_dir.pack(side="left", fill="y", padx=(24, 0))
        self.painel_dir.pack_propagate(False)

        self.info_container = tk.Frame(self.painel_dir, bg=COR_PAINEL)
        self.info_container.pack(expand=True, fill="both")

        # Teclas de atalho pelo teclado físico
        self.bind_all("<Key>", self._tecla_pressionada)
        self.bind_all("<Return>",  lambda e: self._confirmar())
        self.bind_all("<BackSpace>", lambda e: self._corrigir())

    def destroy(self):
        """Remove os bindings globais ao sair da tela."""
        self.unbind_all("<Key>")
        self.unbind_all("<Return>")
        self.unbind_all("<BackSpace>")
        self._after_id = None
        super().destroy()

    # ─── lógica do teclado ──────────────────────────────────────
    def _tecla_pressionada(self, event):
        if event.char.isdigit():
            self._digitar(event.char)

    def _digitar(self, digito: str):
        if self.estado == "confirmado":
            return
        if len(self.digitos) >= self.MAX_DIGITOS:
            return

        self.digitos += digito
        self._atualizar_display()

        # Verifica automaticamente quando atingir o número máximo de dígitos
        if len(self.digitos) == self.MAX_DIGITOS:
            self._verificar_chapa()

    def _corrigir(self):
        """Apaga o último dígito ou limpa tudo se confirmado."""
        if self.estado == "confirmado":
            self._limpar()
            return
        self.digitos = self.digitos[:-1]
        self.estado  = "digitando"
        self._atualizar_display()
        self._limpar_info()

    def _confirmar(self):
        if self.estado == "confirmado":
            self._limpar()
            return
        if not self.digitos:
            return
        if self.estado == "erro":
            self._limpar()
            return

        # Verifica novamente (caso o usuário confirme antes de completar)
        self._verificar_chapa()
        if self.estado == "erro":
            return

        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        if self.digitos not in eleicao.get("chapas", {}):
            self._mostrar_erro()
            return

        ok, msg = GerenciadorDados.registrar_voto(self.chave, self.digitos)
        if ok:
            self.estado = "confirmado"
            self.lbl_display.config(
                text="✔", fg=COR_VERDE, bg=COR_DISPLAY)
            self._mostrar_mensagem_painel(
                "✅  VOTO CONFIRMADO!\n\nAguarde o próximo aluno.",
                COR_VERDE)
            # Limpa automaticamente após 1 segundo
            self._after_id = self.after(1000, self._limpar)
        else:
            messagebox.showerror("Erro", msg)

    def _verificar_chapa(self):
        """Atualiza o painel direito com os dados da chapa digitada."""
        eleicao = GerenciadorDados.obter_eleicao(self.chave)
        chapas  = eleicao.get("chapas", {})

        if self.digitos in chapas:
            info = chapas[self.digitos]
            nomes = _chapa_nomes(info)
            fotos = _chapa_fotos(info)
            self.estado = "digitando"
            self._mostrar_info_chapa(nomes, fotos)
        elif len(self.digitos) == self.MAX_DIGITOS:
            self._mostrar_erro()

    def _mostrar_info_chapa(self, nomes, fotos):
        """Exibe detalhes da chapa no painel direito."""
        self._limpar_info()

        tk.Label(self.info_container, text=f"Chapa {self.digitos}",
                 font=FONTE_SUBTITULO, fg=COR_AMARELO, bg=COR_PAINEL
                 ).pack(pady=(20, 12))

        # Líder
        img1 = _carregar_foto(fotos[0], (90, 90))
        if img1:
            self._fotos_refs.append(img1)
            tk.Label(self.info_container, image=img1,
                     bg=COR_PAINEL).pack(pady=(0, 2))
        tk.Label(self.info_container, text="LÍDER",
                 font=FONTE_STATUS, fg=COR_VERDE, bg=COR_PAINEL).pack()
        tk.Label(self.info_container, text=nomes[0],
                 font=FONTE_NORMAL, fg=COR_TEXTO, bg=COR_PAINEL
                 ).pack(pady=(0, 12))

        # Vice-Líder
        img2 = _carregar_foto(fotos[1], (90, 90))
        if img2:
            self._fotos_refs.append(img2)
            tk.Label(self.info_container, image=img2,
                     bg=COR_PAINEL).pack(pady=(0, 2))
        tk.Label(self.info_container, text="VICE-LÍDER",
                 font=FONTE_STATUS, fg=COR_AZUL, bg=COR_PAINEL).pack()
        tk.Label(self.info_container, text=nomes[1],
                 font=FONTE_NORMAL, fg=COR_TEXTO, bg=COR_PAINEL).pack()

    def _mostrar_mensagem_painel(self, texto, cor):
        """Exibe mensagem no painel direito."""
        self._limpar_info()
        tk.Label(self.info_container, text=texto,
                 font=FONTE_SUBTITULO, fg=cor, bg=COR_PAINEL,
                 wraplength=240, justify="center"
                 ).pack(expand=True)

    def _mostrar_erro(self):
        self.estado = "erro"
        self.lbl_display.config(text="ERRO", fg=COR_VERMELHO, bg=COR_DISPLAY)
        self._mostrar_mensagem_painel(
            "❌  Número de chapa\nnão encontrado.\n\nPressione CORRIGIR.",
            COR_VERMELHO)

    def _atualizar_display(self):
        """Mostra os dígitos digitados com placeholders (_)."""
        placeholders = self.digitos.ljust(self.MAX_DIGITOS, "_")
        self.lbl_display.config(
            text=placeholders, fg=COR_NUMERO, bg=COR_DISPLAY)

    def _limpar(self):
        """Reinicia o estado da urna para o próximo votante."""
        self._after_id = None
        self.digitos = ""
        self.estado  = "digitando"
        self.lbl_display.config(text="", fg=COR_NUMERO, bg=COR_DISPLAY)
        self._limpar_info()

    def _limpar_info(self):
        """Limpa o painel direito."""
        self._fotos_refs.clear()
        for w in self.info_container.winfo_children():
            w.destroy()


# ════════════════════════════════════════════════════════════════
#  TELA DE RESULTADOS
# ════════════════════════════════════════════════════════════════
class TelaResultados(tk.Frame):
    """
    Exibe a apuração da eleição com destaque para a chapa vencedora.
    Só exibe resultados quando a eleição está fechada.
    """

    def __init__(self, parent, app: App, chave: str):
        super().__init__(parent, bg=COR_FUNDO)
        self.app   = app
        self.chave = chave
        rodape(self)
        self._construir()

    def _construir(self):
        eleicao = GerenciadorDados.obter_eleicao(self.chave)

        # ── Cabeçalho ──────────────────────────────────────────
        cab = tk.Frame(self, bg=COR_PAINEL,
                       highlightbackground=COR_BORDA, highlightthickness=1)
        cab.pack(fill="x")
        tk.Label(cab, text="📊  RESULTADOS — " + eleicao["nome"],
                 font=FONTE_SUBTITULO, fg=COR_AMARELO, bg=COR_PAINEL
                 ).pack(pady=12)

        btn(cab, "← Painel", lambda: self.app.ir_para_painel(self.chave),
            cor=COR_CINZA, largura=12, altura=1
            ).pack(side="right", padx=16, pady=10)

        # ── Verificar se eleição está fechada ──────────────────
        if eleicao.get("status") == "aberta":
            tk.Label(self,
                     text="⛔  VOTAÇÃO EM ANDAMENTO\n\n"
                          "Encerre a votação no painel para ver os resultados.",
                     font=FONTE_SUBTITULO, fg=COR_VERMELHO, bg=COR_FUNDO,
                     justify="center"
                     ).pack(expand=True)
            return

        # ── Apuração ────────────────────────────────────────────
        chapas = eleicao.get("chapas", {})
        votos  = eleicao.get("votos",  {})

        # Calcula totais
        total_validos = sum(votos.get(n, 0) for n in chapas)
        total_geral   = sum(votos.values())

        if not chapas:
            tk.Label(self,
                     text="Nenhuma chapa cadastrada nesta eleição.",
                     font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_FUNDO
                     ).pack(expand=True)
            return

        # Descobre vencedor (mais votos dentre as chapas)
        vencedor = max(chapas, key=lambda n: votos.get(n, 0)) if chapas else None
        max_votos = votos.get(vencedor, 0) if vencedor else 0
        empate = (
            sum(1 for n in chapas if votos.get(n, 0) == max_votos) > 1
        ) if max_votos > 0 else False

        # Scroll container
        container = tk.Frame(self, bg=COR_FUNDO)
        container.pack(fill="both", expand=True, padx=24, pady=12)

        canvas = tk.Canvas(container, bg=COR_FUNDO, highlightthickness=0)
        scroll = tk.Scrollbar(container, orient="vertical",
                               command=canvas.yview)
        inner  = tk.Frame(canvas, bg=COR_FUNDO)

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._canvas_wid = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._canvas_wid, width=e.width))

        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._fotos_refs = []  # manter referências das imagens

        # ── Banner do vencedor ─────────────────────────────────
        if total_validos > 0 and not empate:
            info_v = chapas[vencedor]
            nomes_v = _chapa_nomes(info_v)
            fotos_v = _chapa_fotos(info_v)
            banner = tk.Frame(inner, bg="#1e2d0e",
                              highlightbackground=COR_VERDE,
                              highlightthickness=2)
            banner.pack(fill="x", pady=8, ipady=10)

            tk.Label(banner, text="🏆  CHAPA VENCEDORA",
                     font=("Courier New", 13, "bold"),
                     fg=COR_VERDE, bg="#1e2d0e"
                     ).pack(pady=(8, 4))

            # Fotos dos vencedores
            fotos_frame = tk.Frame(banner, bg="#1e2d0e")
            fotos_frame.pack(pady=4)
            for i, (caminho, cargo) in enumerate(
                    zip(fotos_v, ["LÍDER", "VICE-LÍDER"])):
                col = tk.Frame(fotos_frame, bg="#1e2d0e")
                col.pack(side="left", padx=16)
                img = _carregar_foto(caminho, (100, 100))
                if img:
                    self._fotos_refs.append(img)
                    tk.Label(col, image=img, bg="#1e2d0e").pack()
                tk.Label(col, text=cargo, font=FONTE_STATUS,
                         fg=COR_VERDE if cargo == "LÍDER" else COR_AZUL,  # VICE-LÍDER usa azul
                         bg="#1e2d0e").pack()
                tk.Label(col, text=nomes_v[i], font=FONTE_NORMAL,
                         fg=COR_TEXTO, bg="#1e2d0e").pack()

            tk.Label(banner,
                     text=f"Chapa {vencedor}",
                     font=("Courier New", 15, "bold"),
                     fg=COR_AMARELO, bg="#1e2d0e"
                     ).pack()
            tk.Label(banner,
                     text=f"{votos.get(vencedor, 0)} votos  "
                          f"({_pct(votos.get(vencedor, 0), total_validos):.1f}%)",
                     font=FONTE_SUBTITULO, fg=COR_VERDE, bg="#1e2d0e"
                     ).pack(pady=(2, 8))

        elif empate and total_validos > 0:
            tk.Label(inner, text="⚖  EMPATE — Nenhuma chapa tem maioria",
                     font=FONTE_SUBTITULO, fg=COR_AMARELO, bg=COR_FUNDO
                     ).pack(pady=8)

        # ── Tabela de resultados ────────────────────────────────
        tk.Label(inner, text="APURAÇÃO GERAL",
                 font=FONTE_SUBTITULO, fg=COR_TEXTO2, bg=COR_FUNDO
                 ).pack(pady=(8, 4))

        # Ordena pelo número de votos (decrescente)
        chapas_ord = sorted(chapas.items(),
                            key=lambda x: votos.get(x[0], 0),
                            reverse=True)

        for numero, info in chapas_ord:
            nomes   = _chapa_nomes(info)
            qv      = votos.get(numero, 0)
            pct     = _pct(qv, total_validos) if total_validos else 0
            is_win  = (numero == vencedor and not empate and total_validos > 0)

            cor_card = "#1e2d0e" if is_win else COR_PAINEL
            cor_bord = COR_VERDE if is_win else COR_BORDA

            linha = tk.Frame(inner, bg=cor_card,
                             highlightbackground=cor_bord,
                             highlightthickness=1)
            linha.pack(fill="x", pady=3, ipady=6)

            icone = "🥇 " if is_win else "   "
            tk.Label(linha, text=f"{icone}Chapa {numero}",
                     font=FONTE_BOTAO, fg=COR_AMARELO if is_win else COR_TEXTO,
                     bg=cor_card, width=12, anchor="w"
                     ).pack(side="left", padx=12)

            tk.Label(linha, text=f"{nomes[0]}  ·  {nomes[1]}",
                     font=FONTE_NORMAL, fg=COR_TEXTO, bg=cor_card, width=36, anchor="w"
                     ).pack(side="left", padx=4)

            # Barra de progresso
            bar_frame = tk.Frame(linha, bg=cor_card)
            bar_frame.pack(side="left", fill="x", expand=True, padx=12)

            bar_total = tk.Frame(bar_frame, bg=COR_BORDA, height=14)
            bar_total.pack(fill="x", pady=4)
            bar_total.update_idletasks()

            if pct > 0:
                bar_fill = tk.Frame(bar_total,
                                    bg=COR_VERDE if is_win else COR_AZUL,
                                    height=14)
                bar_fill.place(relwidth=pct/100, relheight=1)

            tk.Label(linha, text=f"{qv} votos  ({pct:.1f}%)",
                     font=FONTE_NORMAL, fg=COR_VERDE if is_win else COR_TEXTO,
                     bg=cor_card, width=18, anchor="e"
                     ).pack(side="right", padx=12)

        # ── Rodapé com totais ───────────────────────────────────
        separador(inner).pack(fill="x", pady=10)

        totais = tk.Frame(inner, bg=COR_FUNDO)
        totais.pack()

        for label_txt, valor, cor in [
            ("Total de votos válidos:", str(total_validos), COR_VERDE),
            ("Total geral de votos:",   str(total_geral),   COR_TEXTO),
        ]:
            tk.Label(totais, text=label_txt,
                     font=FONTE_NORMAL, fg=COR_TEXTO2, bg=COR_FUNDO
                     ).pack(side="left", padx=12)
            tk.Label(totais, text=valor,
                     font=FONTE_SUBTITULO, fg=cor, bg=COR_FUNDO
                     ).pack(side="left", padx=(0, 24))


# ─── utilitário ─────────────────────────────────────────────────
def _pct(parte: int, total: int) -> float:
    return (parte / total * 100) if total else 0.0


# ════════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.executar()