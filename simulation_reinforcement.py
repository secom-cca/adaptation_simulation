import numpy as np
import random
import matplotlib.pyplot as plt
from collections import defaultdict
from itertools import product

# 再現性のためのシード設定
random.seed(42)
np.random.seed(42)

# エージェント（部局）の定義
class Agent:
    def __init__(self, name, actions, learning_rate=0.1, discount_factor=0.9):
        self.name = name
        self.actions = actions
        self.q_table = defaultdict(float)
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = 0.1  # 探索率

    def choose_action(self, state):
        if random.random() < self.epsilon:
            action = random.choice(self.actions)
        else:
            q_values = [self.q_table[(state, a)] for a in self.actions]
            max_q = max(q_values)
            # 複数の最大値がある場合はランダムに選択
            action = random.choice([a for a, q in zip(self.actions, q_values) if q == max_q])
        return action

    def update_q_value(self, state, action, reward, next_state):
        old_value = self.q_table[(state, action)]
        next_max = max([self.q_table[(next_state, a)] for a in self.actions])
        new_value = (old_value +
                     self.learning_rate * (reward + self.discount_factor * next_max - old_value))
        self.q_table[(state, action)] = new_value

# 中央集権的エージェントの定義
class CentralizedAgent:
    def __init__(self, actions_space):
        self.actions_space = actions_space  # 各エージェントのアクションスペースの辞書
        self.q_table = defaultdict(float)
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1  # 探索率

        # 全てのアクションの組み合わせを作成
        self.all_action_combinations = list(self._action_combinations())

    def choose_action(self, state):
        if random.random() < self.epsilon:
            action = random.choice(self.all_action_combinations)
        else:
            q_values = [self.q_table[(state, tuple(a.items()))] for a in self.all_action_combinations]
            max_q = max(q_values)
            # 複数の最大値がある場合はランダムに選択
            best_actions = [a for a, q in zip(self.all_action_combinations, q_values) if q == max_q]
            action = random.choice(best_actions)
        return action

    def update_q_value(self, state, actions, reward, next_state):
        old_value = self.q_table[(state, tuple(actions.items()))]
        next_max = max([self.q_table[(next_state, tuple(a.items()))] for a in self.all_action_combinations])
        new_value = (old_value +
                     self.learning_rate * (reward + self.discount_factor * next_max - old_value))
        self.q_table[(state, tuple(actions.items()))] = new_value

    def _action_combinations(self):
        keys = self.actions_space.keys()
        values = self.actions_space.values()
        for combo in product(*values):
            yield dict(zip(keys, combo))

# 環境の定義
class Environment:
    def __init__(self):
        # 初期状態変数
        self.available_water = 100.0
        self.ecosystem_level = 100.0
        self.flood_risk = 0.1
        self.crop_yield = 100.0
        self.year = 2020

        # トレンド
        self.temp_trend = 0.03
        self.precip_trend = -0.2

    def reset(self):
        self.available_water = 100.0
        self.ecosystem_level = 100.0
        self.flood_risk = 0.1
        self.crop_yield = 100.0
        self.year = 2020
        return self.get_state()

    def get_state(self):
        return (round(self.available_water, 1), round(self.ecosystem_level, 1),
                round(self.flood_risk, 2), round(self.crop_yield, 1))

    def step(self, actions):
        # アクションの展開
        irrigation_water = actions['Agriculture_Irrigation']
        released_water = actions['Environment_Release']
        levee_investment = actions['PublicWorks_Levee']
        rnd_investment = actions['Agriculture_RnD']

        # 利用可能水量の更新
        self.available_water += self.precip_trend - irrigation_water - released_water

        # 生態系レベルの更新
        if released_water < 10:
            self.ecosystem_level -= 1
        else:
            self.ecosystem_level += 0.5
        self.ecosystem_level = max(0, min(self.ecosystem_level, 100))

        # 洪水リスクの更新
        self.flood_risk += self.temp_trend - levee_investment * 0.05
        self.flood_risk = max(0, min(self.flood_risk, 1))

        # 作物収量の更新
        self.crop_yield += irrigation_water * 0.5 + rnd_investment * 2 - self.temp_trend * 5
        self.crop_yield = max(0, self.crop_yield)

        # 年の更新
        self.year += 1

        # 各エージェントの報酬の計算
        rewards = {
            'Agriculture': self.crop_yield,  # 作物収量の最大化
            'Environment': self.ecosystem_level,  # 生態系レベルの最大化
            'PublicWorks': -self.flood_risk * 1000  # 洪水リスクの最小化
        }

        # 次の状態の取得
        next_state = self.get_state()

        # シミュレーション終了のチェック
        done = self.year >= 2100

        # 環境状態の記録用
        env_info = {
            'year': self.year,
            'crop_yield': self.crop_yield,
            'ecosystem_level': self.ecosystem_level,
            'flood_risk': self.flood_risk
        }

        # # 全体の利得（例として単純に合計）
        # total_reward = rewards['Agriculture'] + rewards['Environment'] + rewards['PublicWorks']

        # # 調整された報酬関数
        # alpha = 0.1  # 全体の利得を考慮する重み
        # adjusted_rewards = {
        #     'Agriculture': rewards['Agriculture'] + alpha * total_reward,
        #     'Environment': rewards['Environment'] + alpha * total_reward,
        #     'PublicWorks': rewards['PublicWorks'] + alpha * total_reward
        # }

        # # 次の状態と調整された報酬を返す
        # return next_state, adjusted_rewards, done, env_info
        return next_state, rewards, done, env_info

# 分散的シミュレーションの定義
def simulate():
    # エージェントの定義
    agriculture_agent = Agent('Agriculture', actions=[0, 5, 10, 15, 20])
    environment_agent = Agent('Environment', actions=[0, 5, 10, 15, 20])
    public_works_agent = Agent('PublicWorks', actions=[0, 1, 2, 3, 4])
    agriculture_rnd_agent = Agent('Agriculture_RnD', actions=[0, 1, 2, 3, 4])

    agents = [agriculture_agent, environment_agent, public_works_agent, agriculture_rnd_agent]

    # エージェント名とアクションキーのマッピング
    agent_action_keys = {
        'Agriculture': 'Agriculture_Irrigation',
        'Environment': 'Environment_Release',
        'PublicWorks': 'PublicWorks_Levee',
        'Agriculture_RnD': 'Agriculture_RnD'
    }

    # 環境の初期化
    env = Environment()

    # 累積報酬の保存
    cumulative_rewards = {agent.name: [] for agent in agents}

    # アクションと環境状態の保存
    actions_record = {agent.name: [] for agent in agents}
    env_states = []

    # シミュレーションパラメータ
    episodes = 100

    for episode in range(episodes):
        state = env.reset()
        done = False

        # 各エージェントのエピソードごとの累積報酬を初期化
        episode_rewards = {agent.name: 0 for agent in agents}
        episode_actions = {agent.name: [] for agent in agents}
        episode_env_states = []

        while not done:
            # エージェントがアクションを選択
            actions = {
                'Agriculture_Irrigation': agriculture_agent.choose_action(state),
                'Environment_Release': environment_agent.choose_action(state),
                'PublicWorks_Levee': public_works_agent.choose_action(state),
                'Agriculture_RnD': agriculture_rnd_agent.choose_action(state)
            }

            # 環境のステップ
            next_state, rewards, done, env_info = env.step(actions)

            # エージェントがQ値を更新
            for agent in agents:
                action_key = agent_action_keys[agent.name]
                reward_key = agent.name.split('_')[0] if agent.name != 'Agriculture_RnD' else 'Agriculture'
                agent.update_q_value(state, actions[action_key], rewards[reward_key], next_state)

                # エピソード累積報酬の更新
                episode_rewards[agent.name] += rewards[reward_key]
                episode_actions[agent.name].append(actions[action_key])

            # 環境状態の保存
            episode_env_states.append(env_info)

            state = next_state

        # エピソード終了後、累積報酬を保存
        for agent in agents:
            cumulative_rewards[agent.name].append(episode_rewards[agent.name])
            actions_record[agent.name].append(episode_actions[agent.name])

        env_states.append(episode_env_states)

    return cumulative_rewards, actions_record, env_states

# 中央集権的シミュレーションの定義
def simulate_centralized():
    # アクションスペース
    actions_space = {
        'Agriculture_Irrigation': [0, 5, 10, 15, 20],
        'Environment_Release': [0, 5, 10, 15, 20],
        'PublicWorks_Levee': [0, 1, 2, 3, 4],
        'Agriculture_RnD': [0, 1, 2, 3, 4]
    }

    centralized_agent = CentralizedAgent(actions_space)

    # 環境の初期化
    env = Environment()

    # 累積報酬の保存
    cumulative_reward = []
    actions_record = []
    env_states = []

    # シミュレーションパラメータ
    episodes = 100

    for episode in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0
        episode_actions = []
        episode_env_states = []

        while not done:
            # エージェントがアクションを選択
            actions = centralized_agent.choose_action(state)

            # 環境のステップ
            next_state, rewards, done, env_info = env.step(actions)

            # 統合された報酬の定義（例：全ての報酬の合計）
            combined_reward = rewards['Agriculture'] + rewards['Environment'] + rewards['PublicWorks']

            # Q値の更新
            centralized_agent.update_q_value(state, actions, combined_reward, next_state)

            total_reward += combined_reward

            # アクションの保存
            episode_actions.append(actions)

            # 環境状態の保存
            episode_env_states.append(env_info)

            state = next_state

        cumulative_reward.append(total_reward)
        actions_record.append(episode_actions)
        env_states.append(episode_env_states)

    return cumulative_reward, actions_record, env_states

# 両方のシミュレーションを実行し、結果を比較
def main():
    # 分散的シミュレーションの実行
    cumulative_rewards_decentralized, actions_record_decentralized, env_states_decentralized = simulate()

    # 中央集権的シミュレーションの実行
    cumulative_reward_centralized, actions_record_centralized, env_states_centralized = simulate_centralized()

    # 結果の比較プロット

    # 累積報酬のプロット
    plt.figure(figsize=(12, 6))
    for agent_name, rewards in cumulative_rewards_decentralized.items():
        plt.plot(rewards, label=f'Decentralized - {agent_name}')
    plt.plot(cumulative_reward_centralized, label='Centralized Agent', linewidth=3, color='black')
    plt.xlabel('Episode')
    plt.ylabel('Cumulative Reward')
    plt.title('Cumulative Reward')
    plt.legend()
    plt.show()

    # 平均的なアクションの比較（最後のエピソードを使用）
    last_episode_actions_dec = {agent: actions_record_decentralized[agent][-1] for agent in actions_record_decentralized}
    last_episode_actions_cen = actions_record_centralized[-1]

    # アクションの推移をプロット
    plt.figure(figsize=(12, 6))
    for agent in last_episode_actions_dec:
        plt.plot(last_episode_actions_dec[agent], label=f'Decentralized - {agent}')
    for key in ['Agriculture_Irrigation', 'Environment_Release', 'PublicWorks_Levee', 'Agriculture_RnD']:
        actions = [a[key] for a in last_episode_actions_cen]
        plt.plot(actions, label=f'Centralized - {key}', linestyle='--')
    plt.xlabel('Timestep')
    plt.ylabel('Action Value')
    plt.title('Action Comparison (last episode)')
    plt.legend()
    plt.show()

    # 環境状態の推移をプロット
    env_metrics = ['crop_yield', 'ecosystem_level', 'flood_risk']
    for metric in env_metrics:
        plt.figure(figsize=(12, 6))
        # 分散的シミュレーション
        values_dec = [state[metric] for state in env_states_decentralized[-1]]
        plt.plot(values_dec, label='Decentralized')
        # 中央集権的シミュレーション
        values_cen = [state[metric] for state in env_states_centralized[-1]]
        plt.plot(values_cen, label='Centralized', linestyle='--')
        plt.xlabel('Timestep')
        plt.ylabel(metric)
        plt.title(f'{metric} Transition')
        plt.legend()
        plt.show()

if __name__ == "__main__":
    main()
