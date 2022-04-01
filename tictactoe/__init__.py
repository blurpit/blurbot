from typing import List

import numpy as np
from discord import ButtonStyle, Interaction, Member
from discord.ui import View, Button


class TicTacToeButton(Button['TicTacToe']):
    def __init__(self, row, col):
        super().__init__(style=ButtonStyle.secondary, label='\u200b', row=row)
        self.row = row
        self.col = col

    async def callback(self, interaction:Interaction):
        view:TicTacToe = self.view
        state = view.board[self.row][self.col]
        if state in (view.X, view.O):
            return
        if interaction.user != view.get_current_player():
            return

        content = self.select()
        if view.ai_game:
            row, col = view.ai_move()
            content = view.children[row * 3 + col].select()

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = "{} has won!".format(view.player_x.mention)
            elif winner == view.O:
                content = "{} has won!".format(view.player_o.mention)
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)

    def select(self):
        view = self.view
        if view.current_player == view.X:
            self.style = ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.row][self.col] = view.X
            view.current_player = view.O
            return "{}, it's your turn!".format(view.player_o.mention)
        else:
            self.style = ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.row][self.col] = view.O
            view.current_player = view.X
            return "{}, it's your turn!".format(view.player_x.mention)

class TicTacToe(View):
    children:List[TicTacToeButton]
    X = 1
    O = -1
    Tie = 0

    def __init__(self, player_x:Member, player_o:Member, ai_game=False):
        super().__init__()
        if player_x == player_o:
            raise ValueError("Cannot create a game with yourself!")
        self.player_x = player_x
        self.player_o = player_o
        self.ai_game = ai_game

        self.current_player = self.X

        self.board = []
        for row in range(3):
            self.board.append([])
            for col in range(3):
                self.board[row].append(0)
                self.add_item(TicTacToeButton(row, col))

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == self.O * 3:
                return self.O
            elif value == self.X * 3:
                return self.X

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == self.O * 3:
                return self.O
            elif value == self.X * 3:
                return self.X

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == self.O * 3:
            return self.O
        elif diag == self.X * 3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == self.O * 3:
            return self.O
        elif diag == self.X * 3:
            return self.X

        # If we're here, we need to check if a tie was made
        if self.check_board_tie():
            return self.Tie

        return None

    def check_board_tie(self):
        return not np.any(self.board)

    def ai_move(self):
        best_score = -99999
        best_move = [-1, -1]

        for row in range(3):
            for col in range(3):
                if self.board[row][col] == 0:
                    self.board[row][col] = self.O
                    self.i = 0
                    score = self._minimax(0, True)
                    print(self.i)
                    self.board[row][col] = 0

                    if score > best_score:
                        best_move[0] = row
                        best_move[1] = col
                        best_score = score

        return tuple(best_move)

    def _minimax(self, depth, maximizing):
        winner = self.check_board_winner()
        if winner == self.X or winner == self.O:
            return -winner * 10
        elif self.check_board_tie():
            return 0

        best_score = -99999 if maximizing else 99999
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == 0:
                    self.board[row][col] = self.O if maximizing else self.X
                    score = self._minimax(depth + 1, not maximizing)
                    self.i += 1
                    self.board[row][col] = 0
                    best_score = max(best_score, score) if maximizing else min(best_score, score)
        return best_score

    def get_current_player(self):
        return self.player_x if self.current_player == self.X else self.player_o
