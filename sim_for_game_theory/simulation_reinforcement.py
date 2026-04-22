import os
import sys
import argparse
import numpy as np
import random
import matplotlib.pyplot as plt
from collections import defaultdict
from itertools import product
import pickle  # データを保存するため

from backend.src.simulation import simulate_year

# 再現性のためのシード設定
random.seed(42)
np.random.seed(42)

# コマンドライン引数でシナリオ名を取得
def parse_args():
    parser = argparse.ArgumentParser(description='Run the simulation with a specified scenario name.')
    parser.add_argument('--scenario', type=str, default='default', help='Scenario name for the simulation results.')
    args = parser.parse_args()
    return args

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
    def __init__(self, mechanism_design=False, alpha=0.1):
        # 初期状態変数
        self.available_water = 100.0
        self.ecosystem_level = 100.0
        self.flood_risk = 0.1
        self.crop_yield = 100.0
        self.year = 2020
        self.municipal_demand = 100
        self.levee_investment_years = 0
        self.levee_level = 0
        self.high_temp_torelance_level = 0
        self.RnD_investment_years = 0

        # トレンド
        self.temp_trend = 0.03
        self.precip_trend = -0.2

        # メカニズムデザインの適用フラグとパラメータ
        self.mechanism_design = mechanism_design
        self.alpha = alpha  # 全体の利得を考慮する重み

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

        # 意思決定変数を辞書にまとめる
        decision_vars = {
            'irrigation_water_amount': irrigation_water,
            'released_water_amount': released_water,
            'levee_construction_cost': levee_investment,
            'agricultural_RnD_cost': rnd_investment
        }

        # 現在の状態を辞書にまとめる
        prev_values = {
            'municipal_demand': self.municipal_demand,
            'available_water': self.available_water,
            'levee_level': self.levee_level,
            'high_temp_tolerance_level': self.high_temp_torelance_level,
            'ecosystem_level': self.ecosystem_level,
            'levee_investment_years': self.levee_investment_years,
            'RnD_investment_years': self.RnD_investment_years
        }

        # パラメータ設定
        params = {
            'start_year': 2020,
            'base_temp': 15.0,
            'temp_trend': self.temp_trend,
            'temp_uncertainty': 0.5,
            'base_precip': 1000.0,
            'precip_trend': self.precip_trend,
            'base_precip_uncertainty': 100.0,
            'precip_uncertainty_trend': 5.0,
            'initial_hot_days': 10.0,
            'temp_to_hot_days_coeff': 1.5,
            'hot_days_uncertainty': 3.0,
            'base_extreme_precip_freq': 0.1,
            'extreme_precip_freq_trend': 0.01,
            'municipal_demand_trend': 0.02,
            'municipal_demand_uncertainty': 0.005,
            'temp_coefficient': 0.1,
            'max_potential_yield': 100.0,
            'optimal_irrigation_amount': 50.0,
            'flood_damage_coefficient': 1000,
            'levee_level_increment': 0.05,
            'high_temp_tolerance_increment': 0.02,
            'levee_investment_threshold': 5.0,
            'RnD_investment_threshold': 5.0,
            'levee_investment_required_years': 3,
            'RnD_investment_required_years': 2,
            'max_available_water': 200.0,
            'evapotranspiration_amount': 50.0,
            'ecosystem_threshold': 50.0
        }

        # simulate_year関数を使って次の年の結果を計算
        current_values, outputs = simulate_year(self.year, prev_values, decision_vars, params)

        # 状態の更新
        self.available_water = current_values['available_water']
        self.ecosystem_level = current_values['ecosystem_level']
        self.flood_risk = outputs['Flood Damage']
        self.crop_yield = current_values['crop_yield']

        self.municipal_demand = current_values['municipal_demand']
        self.levee_investment_years = current_values['levee_investment_years']
        self.levee_level = current_values['levee_level']
        self.high_temp_torelance_level = current_values['high_temp_tolerance_level']
        self.RnD_investment_years = current_values['RnD_investment_years']

        self.year += 1

        # 各エージェントの報酬の計算
        rewards = {
            'Agriculture': self.crop_yield,  # 作物収量の最大化
            'Environment': self.ecosystem_level,  # 生態系レベルの最大化
            'PublicWorks': -self.flood_risk # + self.levee_level  # 洪水リスクの最小化
        }

        # メカニズムデザインの適用
        if self.mechanism_design:
            total_reward = sum(rewards.values())
            adjusted_rewards = {}
            for key in rewards:
                adjusted_rewards[key] = rewards[key] + self.alpha * total_reward
            rewards = adjusted_rewards

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

        return next_state, rewards, done, env_info


# シャープレイ値を用いた協力シミュレーションの定義
def simulate_shapley():
    # エージェントの定義（協力）
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

    # シャープレイ値の計算（ここでは簡略化）
    # 実際には全ての可能な連合を考慮する必要がありますが、例として均等配分とします
    shapley_values = {agent.name: 1 / len(agents) for agent in agents}

    for episode in range(episodes):
        state = env.reset()
        done = False

        # 各エージェントのエピソードごとの累積報酬を初期化
        episode_rewards = {agent.name: 0 for agent in agents}
        episode_actions = {agent.name: [] for agent in agents}
        episode_env_states = []

        while not done:
            # エージェントがアクションを選択（協力的に最適化されたアクションを選択する仮定）
            # ここでは中央集権的エージェントと同じ行動を取ると仮定
            actions_space = {
                'Agriculture_Irrigation': agriculture_agent.actions,
                'Environment_Release': environment_agent.actions,
                'PublicWorks_Levee': public_works_agent.actions,
                'Agriculture_RnD': agriculture_rnd_agent.actions
            }
            centralized_agent = CentralizedAgent(actions_space)
            actions = centralized_agent.choose_action(state)

            # 環境のステップ
            next_state, rewards, done, env_info = env.step(actions)

            # 各エージェントの報酬をシャープレイ値に基づいて分配
            total_reward = sum(rewards.values())
            for agent in agents:
                agent_reward = shapley_values[agent.name] * total_reward
                agent.update_q_value(state, actions[agent_action_keys[agent.name]], agent_reward, next_state)
                episode_rewards[agent.name] += agent_reward
                episode_actions[agent.name].append(actions[agent_action_keys[agent.name]])

            # 環境状態の保存
            episode_env_states.append(env_info)

            state = next_state

        # エピソード終了後、累積報酬を保存
        for agent in agents:
            cumulative_rewards[agent.name].append(episode_rewards[agent.name])
            actions_record[agent.name].append(episode_actions[agent.name])

        env_states.append(episode_env_states)

    return cumulative_rewards, actions_record, env_states

# 分散的シミュレーションの定義
def simulate(mechanism_design=False, alpha=0.1):
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
    env = Environment(mechanism_design=mechanism_design, alpha=alpha)

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
            combined_reward = sum(rewards.values())

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
    args = parse_args()
    scenario_name = args.scenario

    # 結果を保存するフォルダの作成
    result_dir = os.path.join('result', scenario_name)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # 分散的シミュレーションの実行
    cumulative_rewards_decentralized, actions_record_decentralized, env_states_decentralized = simulate()

    # 中央集権的シミュレーションの実行
    cumulative_reward_centralized, actions_record_centralized, env_states_centralized = simulate_centralized()

    # メカニズムデザインを適用した分散的シミュレーションの実行
    cumulative_rewards_mechanism, actions_record_mechanism, env_states_mechanism = simulate(mechanism_design=True, alpha=0.1)

    # シャープレイ値を用いた協力シミュレーションの実行
    cumulative_rewards_shapley, actions_record_shapley, env_states_shapley = simulate_shapley()

    # 結果の比較プロット

    # 累積報酬のプロット
    plt.figure(figsize=(12, 6))
    for agent_name, rewards in cumulative_rewards_decentralized.items():
        plt.plot(rewards, label=f'Decentralized - {agent_name}')
    plt.plot(cumulative_reward_centralized, label='Centralized Agent', linewidth=3, color='black')
    for agent_name, rewards in cumulative_rewards_mechanism.items():
        plt.plot(rewards, label=f'Mechanism Design - {agent_name}', linestyle='--')
    for agent_name, rewards in cumulative_rewards_shapley.items():
        plt.plot(rewards, label=f'Shapley - {agent_name}', linestyle=':')
    plt.xlabel('Episode')
    plt.ylabel('Cumulative Reward')
    plt.title('Comparison of Cumulative Rewards')
    plt.legend()
    plt.savefig(os.path.join(result_dir, 'cumulative_rewards.png'))
    plt.close()

    # 平均的なアクションの比較（最後のエピソードを使用）
    last_episode_actions_dec = {agent: actions_record_decentralized[agent][-1] for agent in actions_record_decentralized}
    last_episode_actions_cen = actions_record_centralized[-1]
    last_episode_actions_mech = {agent: actions_record_mechanism[agent][-1] for agent in actions_record_mechanism}
    last_episode_actions_shapley = {agent: actions_record_shapley[agent][-1] for agent in actions_record_shapley}

    # アクションの推移をプロット
    plt.figure(figsize=(12, 6))
    for agent in last_episode_actions_dec:
        plt.plot(last_episode_actions_dec[agent], label=f'Decentralized - {agent}')
    for key in ['Agriculture_Irrigation', 'Environment_Release', 'PublicWorks_Levee', 'Agriculture_RnD']:
        actions = [a[key] for a in last_episode_actions_cen]
        plt.plot(actions, label=f'Centralized - {key}', linestyle='--')
    for agent in last_episode_actions_mech:
        plt.plot(last_episode_actions_mech[agent], label=f'Mechanism Design - {agent}', linestyle=':')
    for agent in last_episode_actions_shapley:
        plt.plot(last_episode_actions_shapley[agent], label=f'Shapley - {agent}', linestyle='-.')
    plt.xlabel('Timestep')
    plt.ylabel('Action Value')
    plt.title('Action Comparison (Last Episode)')
    plt.legend()
    plt.savefig(os.path.join(result_dir, 'action_comparison.png'))
    plt.close()

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
        # メカニズムデザイン
        values_mech = [state[metric] for state in env_states_mechanism[-1]]
        plt.plot(values_mech, label='Mechanism Design', linestyle=':')
        # シャープレイ値
        values_shapley = [state[metric] for state in env_states_shapley[-1]]
        plt.plot(values_shapley, label='Shapley', linestyle='-.')
        plt.xlabel('Timestep')
        plt.ylabel(metric)
        plt.title(f'Transition of {metric}')
        plt.legend()
        plt.savefig(os.path.join(result_dir, f'{metric}_transition.png'))
        plt.close()

    # データの保存
    with open(os.path.join(result_dir, 'data_decentralized.pkl'), 'wb') as f:
        pickle.dump({
            'cumulative_rewards': cumulative_rewards_decentralized,
            'actions_record': actions_record_decentralized,
            'env_states': env_states_decentralized
        }, f)

    with open(os.path.join(result_dir, 'data_centralized.pkl'), 'wb') as f:
        pickle.dump({
            'cumulative_reward': cumulative_reward_centralized,
            'actions_record': actions_record_centralized,
            'env_states': env_states_centralized
        }, f)

    with open(os.path.join(result_dir, 'data_mechanism_design.pkl'), 'wb') as f:
        pickle.dump({
            'cumulative_rewards': cumulative_rewards_mechanism,
            'actions_record': actions_record_mechanism,
            'env_states': env_states_mechanism
        }, f)

    with open(os.path.join(result_dir, 'data_shapley.pkl'), 'wb') as f:
        pickle.dump({
            'cumulative_rewards': cumulative_rewards_shapley,
            'actions_record': actions_record_shapley,
            'env_states': env_states_shapley
        }, f)

if __name__ == "__main__":
    main()
