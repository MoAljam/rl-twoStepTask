from agents.model_based import AgentModelBased
from agents.model_free import AgentModelFree
from agents.hybrid import HybridAgent
from agents.random_agent import RandomAgent
from environment import TwoStepEnv
from utils import random_walk_gaussian
import pandas as pd
import numpy as np


def simulate(agent_type='random', trials=200, seed=None, verbose=False, params:dict={}, from_data:pd.DataFrame=None):
    if verbose:
        print(f"Simulating {agent_type} agent, {trials} trials.")
        print(f"Agent parameters: {params if params else 'default'}")
    # set a random seed
    np.random.seed(seed)

    # simulate the task
    action_space = TwoStepEnv.action_space
    state_space = TwoStepEnv.state_space

    if agent_type == 'model_based':
        agent = AgentModelBased(action_space, state_space, **params)
    elif agent_type == 'model_free':
        agent = AgentModelFree(action_space, state_space, **params)
    elif agent_type == 'hybrid' or agent_type.startswith('hybrid'):
        agent = HybridAgent(action_space, state_space, **params)
    else:
        agent = RandomAgent(action_space, state_space, **params)
    env = TwoStepEnv()
    task_data = simulate_two_step_task(env, agent, trials=trials, from_data=from_data)

    # convert the data to a dataframe
    task_df = pd.DataFrame.from_dict(task_data, orient='index')

    # unset the random seed
    np.random.seed(None)
    return task_df, agent

def simulate_two_step_task(env: TwoStepEnv, agent=None, trials=200,
                           policy_method="softmax", from_data:pd.DataFrame=None):
    env.reset()
    if from_data is not None:
        reward_probabilities = from_data['rewardProbabilities'].iloc[0]
        # reshape the reward probabilities to the correct shape, with zeros for the first stage
        # self.reward_prob_matrix = np.array(
        #     [[0, 0],  # first stage (state 0) for both actions
        #      [p_1_0, p_1_1],  # second stage (state 1) for both actions
        #      [p_2_0, p_2_1]])  # second stage (state 2) for both actions
        reward_probabilities = np.array([0, 0, *reward_probabilities])
        # reshape
        reward_probabilities = reward_probabilities.reshape((3, 2))
        print(reward_probabilities)
        
        env.set_reward_probabilities(reward_probabilities)

    task_data = {}

    sd_for_random_walk = 0.025
    time_step = 0
    while time_step < trials:
        # first stage choice
        terminal = False
        while not terminal:
            current_state = env.state
            if agent:
                action = agent.policy(env.state, method=policy_method)
            else:  # if no agent is given -> random action
                action = np.random.choice(env.action_space)

            next_state, reward, terminal, info = env.step(action)

            if agent:
                agent.update_beliefs(current_state, action, reward, next_state,
                                     terminal)

        info['trial_index'] = int(time_step)
        task_data[time_step] = info
        env.reset()
        if from_data is not None and time_step < trials - 1:
            new_reward_prob_matrix = from_data['rewardProbabilities'].iloc[time_step + 1]
            # include zeros for the first stage
            new_reward_prob_matrix = np.array([0, 0, *new_reward_prob_matrix])
            # reshape to the epxpected shape (3, 2): state-action
            new_reward_prob_matrix = new_reward_prob_matrix.reshape((3, 2))
            print(new_reward_prob_matrix)
        else:    
            new_reward_prob_matrix = random_walk_gaussian(env.reward_prob_matrix,
                                                      sd_for_random_walk)
        env.set_reward_probabilities(new_reward_prob_matrix)
        time_step += 1

    return task_data
