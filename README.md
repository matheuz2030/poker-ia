# ♠️ Texas Hold'em Poker AI — Simulador de Personalidades e Decisão sob Incerteza

Projeto acadêmico e prático de Inteligência Artificial aplicada ao **Texas Hold'em Poker**. O projeto simula a tomada de decisão em tempo real sob incerteza utilizando o método de **Monte Carlo**, cálculo de **Pot Odds** e modelagem de **4 perfis comportamentais de risco**.

---

## 🎯 Visão Geral do Projeto

O sistema conta com duas interfaces completas:
1. **Interface Pygame (`gui_pygame.py`):** Simulação visual estilo mesa de poker com 4 jogadores de IA com perfis distintos competindo entre si, suporte a modo passo a passo, modo contínuo (*Auto-Play*), modo de visualização de cartas (*Modo Revelar*) e analisador tático de jogadas (*Pop-up de Destaques*).
2. **Interface Streamlit (`app.py`):** Jogo interativo *Humano vs IA* com dashboard telemétrico em tempo real.

---

## 🎭 Perfis de IA Implementados

| Perfil | Arquétipo | Estratégia / Viés |
| :--- | :--- | :--- |
| ♠ **IA Racional** | Equilibrada | Decisão matemática estrita por $Equity \ge Pot\ Odds$. Foco em valor esperado (EV+). |
| ♥ **IA Ousada** | Agressiva | Assume mais riscos com threshold de Equity reduzido em $15\%$. Pressiona com apostas frequentes. |
| ♦ **IA Cautelosa** | Conservadora | Exige $+15\%$ de margem de segurança na Equity para continuar na mão. Foco em proteção de fichas. |
| ♣ **IA Blefadora** | Wildcard | Possui $20\%$ de chance de mandar um *Raise alto* mesmo segurando mãos fracas para forçar desistências. |

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.10+**
* **Pygame-CE:** Interface gráfica interativa 2D.
* **Streamlit:** Interface web analítica.
* **Treys:** Motor bitwise de alta performance para avaliação matemática de mãos de poker.

---

## 🚀 Como Executar

### 1. Clonar o Repositório e Instalar Dependências

```bash
git clone https://github.com/SEU_USUARIO/poker-ai.git
cd poker-ai
pip install -r requirements.txt
```

### 2. Executar a Simulação Visual (Pygame)

```bash
python gui_pygame.py
```

#### Tutorial integrado: Academia Poker Royale

No menu principal, clique em **COMO JOGAR & CONHEÇA AS IAs**. No lobby IA vs humano, use **COMO JOGAR & GUIA DAS IAs**. O tutorial tem **seis telas visuais**, em português simples, para uma explicação de aproximadamente cinco minutos: como ganhar, abertura das cartas, pensamento da IA, preço de continuar, diferenças dos personagens e regras do motor.

Cada tela usa cartas, fichas ou diagramas e uma explicação de até 45 palavras. O formato já tem letras grandes para projeção, sem capítulos extensos nem alternância de modos. Use **Anterior / Próximo**, **← / →**, **Espaço** ou **Enter** para navegar. Na segunda tela, **Abrir próxima carta** (ou **O**) demonstra a abertura das três primeiras, da quarta e da última carta. **Concluir** ou **Voltar / ESC** retorna ao lobby de origem e preserva suas escolhas.

No desktop, as seis telas cabem sem rolagem. Em telas estreitas, os exemplos se reorganizam verticalmente; use a roda do mouse, as setas para cima/baixo ou arraste com o dedo quando necessário. Os exemplos são fictícios e não executam decisões da IA, não avançam a partida nem alteram seus sorteios.

#### ⌨️ Controles no Pygame:
* **`ESPAÇO`:** Avança a próxima ação passo a passo.
* **`A`:** Alterna o modo **Auto-Play** (automático).
* **`D`:** Alterna o **Modo Revelar Cartas** (Modo Deus).
* **`V` (Segurar):** Espia a mesa por trás do Pop-up de Destaque.
* **`H`:** Abre o histórico de curiosidades e recordes, inclusive em Humano vs IA.
* **Curiosidades:** Ao terminar uma mão, reabre o resumo com o nome da jogada,
  suas cinco cartas e RGB nas cartas da combinação (sem destacar cartas de desempate).
  Vitórias por desistência não recebem combinações de cartas que não foram abertas.
  Comparações “E se?” são identificadas como hipóteses; no modo humano, só analisam
  a desistência do próprio jogador, preservando as cartas ocultas dos oponentes.
* **`R`:** Reinicia os stacks e contadores de vitórias.
* **`ESC`:** Retorna à Tela Inicial / Menu.

### 3. Executar o Teste Automatizado de 50 Partidas (Headless)

```bash
python test_simulation.py
```

### 4. Executar a Versão Web Humano vs IA (Streamlit)

```bash
streamlit run app.py
```

---

## 📄 Licença

Este projeto é de código aberto sob a licença [MIT](LICENSE).


## Tela de partida atualizada

A interface Pygame usa a mesa e as artes fornecidas em `assets/game/`.
`game_view.py` cuida dos perfis, seleção de cartas e animações; `card_design.py`
gera as 52 combinações de valor e naipe a partir das artes de referência.
O motor de regras e as estratégias de Monte Carlo continuam em seus módulos originais.

- **JOGAR** inicia automaticamente uma mão com Ronaldo, Mbappé, Messi e Neymar.
- O modo automático aguarda a distribuição e os flips antes de avançar os turnos.
- Ao fim da mão, o jogo pausa para apresentar o resultado. **A** inicia outra mão.
- **ESPAÇO** permite avançar manualmente; **D** alterna a revelação das cartas.
- Clique ou toque numa carta para selecioná-la. `GameView.on_card_click` é o ponto
  de extensão para novas ações; a seleção não modifica o estado do pôquer.
- A janela pode ser redimensionada. A mesa conserva sua proporção e os cliques
  são convertidos para as coordenadas da composição.

Verificação: `python -m unittest discover -s tests -v`.
