from enum import Enum
import random


class GameState:
    def __init__(self, best_of=1):
        self.best_of = best_of  # 几局制
        self.player_score = 0   # 玩家得分
        self.computer_score = 0 # 电脑得分
        self.rounds_played = 0  # 已玩回合数

    def update_score(self, player_wins):
        """更新比分"""
        if player_wins:
            self.player_score += 1
        else:
            self.computer_score += 1
        self.rounds_played += 1

    def get_score_string(self):
        """获取比分字符串"""
        return f"{self.player_score} - {self.computer_score}"

    def is_game_over(self):
        """检查游戏是否结束"""
        target_score = (self.best_of // 2) + 1
        return self.player_score >= target_score or self.computer_score >= target_score

    def get_winner(self):
        """获取获胜者"""
        if self.player_score > self.computer_score:
            return "玩家"
        elif self.computer_score > self.player_score:
            return "电脑"
        return "平局"


class GameLogic:
    def __init__(self):
        self.game_state = GameState()
        self.moves = ["rock", "paper", "scissors"]

    def get_random_move(self):
        """获取随机手势"""
        return random.choice(self.moves)

    def get_winning_move(self, player_move):
        """获取能击败玩家手势的手势"""
        winning_moves = {
            "rock": "paper",
            "paper": "scissors",
            "scissors": "rock"
        }
        return winning_moves.get(player_move, self.get_random_move())

    def get_losing_move(self, player_move):
        """获取会输给玩家手势的手势"""
        losing_moves = {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper"
        }
        return losing_moves.get(player_move, self.get_random_move())

    def judge_round(self, player_move, computer_move):
        """判断回合胜负"""
        # 判断胜负规则
        winning_combinations = {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper"
        }

        # 判断结果
        if player_move == computer_move:
            message = "平局！重新开始本轮"
            player_wins = None  # 平局不计分
        elif winning_combinations[player_move] == computer_move:
            message = "玩家胜利！"
            player_wins = True
        else:
            message = "电脑胜利！"
            player_wins = False

        # 只在非平局时更新游戏状态
        if player_wins is not None:
            self.game_state.update_score(player_wins)

        # 返回结果
        result = {
            "message": message,
            "score": self.game_state.get_score_string(),
            "game_over": self.game_state.is_game_over(),
            "winner": self.game_state.get_winner() if self.game_state.is_game_over() else None
        }

        return result

    def reset_game(self, best_of=1):
        """重置游戏状态"""
        self.game_state = GameState(best_of=best_of)