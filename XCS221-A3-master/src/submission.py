import math, random
from collections import defaultdict
from typing import List, Callable, Tuple, Dict, Any, Optional, Iterable, Set
import gymnasium as gym
import numpy as np

import util
from util import ContinuousGymMDP, StateT, ActionT
from custom_mountain_car import CustomMountainCarEnv

############################################################
# Problem 3a
# Implementing Value Iteration on Number Line (from Problem 1)
"""
Given transition probabilities and rewards, computes and returns V and
the optimal policy pi for each state.
- succAndRewardProb: Dictionary mapping tuples of (state, action) to a list of (nextState, prob, reward) Tuples.
- Returns: Dictionary mapping each state to an action.
"""


def valueIteration(
    succAndRewardProb: Dict[Tuple[StateT, ActionT], List[Tuple[StateT, float, float]]],
    discount: float,
    epsilon: float = 0.001,
):
    # Define a mapping from states to Set[Actions] so we can determine all the actions that can be taken from s.
    # You may find this useful in your approach.
    stateActions = defaultdict(set)
    for state, action in succAndRewardProb.keys():
        stateActions[state].add(action)

    def computeQ(V: Dict[StateT, float], state: StateT, action: ActionT) -> float:
        # Return Q(state, action) based on V(state)
        # pass
        # ### START CODE HERE ###
        q_value = 0
        for next_state, prob, reward in succAndRewardProb[(state, action)]:
            q_value += prob * (reward + discount * V[next_state])
        return q_value
        # ### END CODE HERE ###

    def computePolicy(V: Dict[StateT, float]) -> Dict[StateT, ActionT]:
        # Return the policy given V.
        # pass
        # ### START CODE HERE ###
        policy = {}
        for state in stateActions.keys():
            best_action = max(
                stateActions[state], key=lambda action: computeQ(V, state, action)
            )
            policy[state] = best_action
        return policy
        # ### END CODE HERE ###

    print("Running valueIteration...")
    V = defaultdict(
        float
    )  # This will return 0 for states not seen (handles terminal states)
    numIters = 0
    while True:
        newV = defaultdict(
            float
        )  # This will return 0 for states not seen (handles terminal states)
        # update V values using the computeQ function above.
        # repeat until the V values for all states converge (changes between iterations are less than epsilon).
        # ### START CODE HERE ###
        for state in stateActions.keys():
            newV[state] = max(
                computeQ(V, state, action) for action in stateActions[state]
            )
        max_change = max(abs(V[state] - newV[state]) for state in V.keys())
        if max_change < epsilon:
            break
        # ### END CODE HERE ###
        V = newV
        numIters += 1
    V_opt = V
    print(("valueIteration: %d iterations" % numIters))
    return computePolicy(V_opt)


############################################################
# Problem 3b
# Model-Based Monte Carlo


# Runs value iteration algorithm on the number line MDP
# and prints out optimal policy for each state.
def run_VI_over_numberLine(mdp: util.NumberLineMDP):
    succAndRewardProb = {
        (-mdp.n + 1, 1): [
            (-mdp.n + 2, 0.2, mdp.penalty),
            (-mdp.n, 0.8, mdp.leftReward),
        ],
        (-mdp.n + 1, 2): [
            (-mdp.n + 2, 0.3, mdp.penalty),
            (-mdp.n, 0.7, mdp.leftReward),
        ],
        (mdp.n - 1, 1): [(mdp.n - 2, 0.8, mdp.penalty), (mdp.n, 0.2, mdp.rightReward)],
        (mdp.n - 1, 2): [(mdp.n - 2, 0.7, mdp.penalty), (mdp.n, 0.3, mdp.rightReward)],
    }

    for s in range(-mdp.n + 2, mdp.n - 1):
        succAndRewardProb[(s, 1)] = [
            (s + 1, 0.2, mdp.penalty),
            (s - 1, 0.8, mdp.penalty),
        ]
        succAndRewardProb[(s, 2)] = [
            (s + 1, 0.3, mdp.penalty),
            (s - 1, 0.7, mdp.penalty),
        ]

    pi = valueIteration(succAndRewardProb, mdp.discount)
    return pi


class ModelBasedMonteCarlo(util.RLAlgorithm):
    def __init__(
        self,
        actions: List[ActionT],
        discount: float,
        calcValIterEvery: int = 10000,
        explorationProb: float = 0.2,
    ) -> None:
        self.actions = actions
        self.discount = discount
        self.calcValIterEvery = calcValIterEvery
        self.explorationProb = explorationProb
        self.numIters = 0

        # (state, action) -> {nextState -> ct} for all nextState
        self.tCounts = defaultdict(lambda: defaultdict(int))
        # (state, action) -> {nextState -> totalReward} for all nextState
        self.rTotal = defaultdict(lambda: defaultdict(float))

        self.pi = {}  # Optimal policy for each state. state -> action

    # This algorithm will produce an action given a state.
    # Here we use the epsilon-greedy algorithm: with probability |explorationProb|, take a random action.
    # Should return random action if the given state is not in self.pi.
    # The input boolean |explore| indicates whether the RL algorithm is in train or test time. If it is false (test), we
    # should always follow the policy if available.
    def getAction(self, state: StateT, explore: bool = True) -> ActionT:
        if explore:
            self.numIters += 1
        explorationProb = self.explorationProb
        if self.numIters < 2e4:  # Always explore
            explorationProb = 1.0
        elif (
            self.numIters > 1e6
        ):  # Lower the exploration probability by a logarithmic factor.
            explorationProb = explorationProb / math.log(self.numIters - 100000 + 1)
        # ### START CODE HERE ###
        if random.random() < explorationProb or state not in self.pi:
            return random.choice(self.actions)
        else:
            return self.pi[state]
        # ### END CODE HERE ###

    # We will call this function with (s, a, r, s'), which is used to update tCounts and rTotal.
    # For every self.calcValIterEvery steps, runs value iteration after estimating succAndRewardProb.
    def incorporateFeedback(
        self,
        state: StateT,
        action: ActionT,
        reward: int,
        nextState: StateT,
        terminal: bool,
    ):

        self.tCounts[(state, action)][nextState] += 1
        self.rTotal[(state, action)][nextState] += reward

        if self.numIters % self.calcValIterEvery == 0:
            # Estimate succAndRewardProb based on self.tCounts and self.rTotal.
            # Then run valueIteration and update self.pi.
            succAndRewardProb = defaultdict(list)
            # ### START CODE HERE ###
            for (state, action), rewards in self.rTotal.items():
                total_count = sum(self.tCounts[(state, action)].values())
                for next_state, reward_sum in rewards.items():
                    prob = self.tCounts[(state, action)][next_state] / total_count
                    succAndRewardProb[(state, action)].append(
                        (next_state, prob, reward_sum / total_count)
                    )
            # Run value iteration
            self.pi = valueIteration(succAndRewardProb, self.discount)
            # ### END CODE HERE ###


############################################################
# Problem 4a
# Performs Tabular Q-learning. Read util.RLAlgorithm for more information.
"""
- actions: the list of valid actions
- discount: a number between 0 and 1, which determines the discount factor
- explorationProb: the epsilon value indicating how frequently the policy returns a random action
- intialQ: the value for intializing Q values.
"""


class TabularQLearning(util.RLAlgorithm):
    def __init__(
        self,
        actions: List[ActionT],
        discount: float,
        explorationProb: float = 0.2,
        initialQ: float = 0,
    ):
        self.actions = actions
        self.discount = discount
        self.explorationProb = explorationProb
        self.Q = defaultdict(lambda: initialQ)
        self.numIters = 0

    # This algorithm will produce an action given a state.
    # Here we use the epsilon-greedy algorithm: with probability |explorationProb|, take a random action.
    # The input boolean |explore| indicates whether the RL algorithm is in train or test time. If it is false (test), we
    # should always choose the maximum Q-value action.
    def getAction(self, state: StateT, explore: bool = True) -> ActionT:
        if explore:
            self.numIters += 1
        explorationProb = self.explorationProb
        if self.numIters < 2e4:  # explore
            explorationProb = 1.0
        elif (
            self.numIters > 1e5
        ):  # Lower the exploration probability by a logarithmic factor.
            explorationProb = explorationProb / math.log(self.numIters - 100000 + 1)

        # ### START CODE HERE ###
        if explore and random.random() < self.explorationProb:
            return random.choice(self.actions)
        else:
            # Perform exploitation
            return max(self.actions, key=lambda a: self.Q[(state, a)])
        # ### END CODE HERE ###

    # Call this function to get the step size to update the weights.
    def getStepSize(self) -> float:
        return 0.1

    # We will call this function with (s, a, r, s'), which you should use to update |Q|.
    # Note that if s is a terminal state, then terminal will be True.  Remember to check for this.
    # You should update the Q values using self.getStepSize()
    def incorporateFeedback(
        self,
        state: StateT,
        action: ActionT,
        reward: float,
        nextState: StateT,
        terminal: bool,
    ) -> None:
        # pass
        # ### START CODE HERE ###
        if terminal:
            target = reward
        else:
            target = reward + self.discount * max(
                self.Q[(nextState, a)] for a in self.actions
            )
        self.Q[(state, action)] += self.getStepSize() * (
            target - self.Q[(state, action)]
        )
        # ### END CODE HERE ###

############################################################
# Problem 4b: Fourier feature extractor
def fourierFeatureExtractor(
        state: StateT,
        action: ActionT,
        maxCoeff: int = 5,
        scale: Optional[Iterable] = None
    ) -> np.ndarray:
    '''
    For state (x, y, z), maxCoeff 2, and scale [2, 1, 1], this should output (in any order):
    [1, cos(pi * 2x), cos(pi * y), cos(pi * z),
     cos(pi * (2x + y)), cos(pi * (2x + z)), cos(pi * (y + z)),
     cos(pi * (4x)), cos(pi * (2y)), cos(pi * (2z)),
     cos(pi*(4x + y)), cos(pi * (4x + z)), ..., cos(pi * (4x + 2y + 2z))]
    '''
    if scale is None:
        scale = np.ones_like(state)
    features = None

    # Below, implement the fourier feature extractor as similar to the doc string provided.
    # The return shape should be 1 dimensional ((maxCoeff+1)^(len(state)),).
    #
    # HINT: refer to util.polynomialFeatureExtractor as a guide for
    # doing efficient arithmetic broadcasting in numpy.

    # ### START CODE HERE ###
    features = []
    max_combinations = (maxCoeff + 1) ** len(state)

    for i in range(max_combinations):
        coeff_tuple = np.base_repr(i, maxCoeff + 1).zfill(len(state))
        coeff_tuple = tuple(map(int, coeff_tuple))
        value = np.cos(np.pi * np.sum(np.array(state) * np.array(scale) * np.array(coeff_tuple)))
        features.append(value)

    features= np.array(features)

    # ### END CODE HERE ###

    return features

############################################################
# Problem 4c: Q-learning with Function Approximation
# Performs Function Approximation Q-learning. Read util.RLAlgorithm for more information.
"""
- featureDim: the dimensionality of the output of the feature extractor
- featureExtractor: a function that takes a state and action and returns a numpy array representing the feature.
- actions: the list of valid actions
- discount: a number between 0 and 1, which determines the discount factor
- explorationProb: the epsilon value indicating how frequently the policy returns a random action
"""


class FunctionApproxQLearning(util.RLAlgorithm):
    def __init__(
        self,
        featureDim: int,
        featureExtractor: Callable,
        actions: List[int],
        discount: float,
        explorationProb=0.2,
    ):
        self.featureDim = featureDim
        self.featureExtractor = featureExtractor
        self.actions = actions
        self.discount = discount
        self.explorationProb = explorationProb
        self.W = np.random.standard_normal(size=(featureDim, len(actions)))
        self.numIters = 0

    def getQ(self, state: np.ndarray, action: int) -> float:
        # pass
        # ### START CODE HERE ###
        features = self.featureExtractor(
            state, action
        )  # Get features for the state-action pair
        return np.dot(features, self.W[:, action])
        # ### END CODE HERE ###

    # This algorithm will produce an action given a state.
    # Here we use the epsilon-greedy algorithm: with probability |explorationProb|, take a random action.
    # The input boolean |explore| indicates whether the RL algorithm is in train or test time. If it is false (test), we
    # should always choose the maximum Q-value action.
    def getAction(self, state: np.ndarray, explore: bool = True) -> int:
        if explore:
            self.numIters += 1
        explorationProb = self.explorationProb
        if self.numIters < 2e4:  # Always explore
            explorationProb = 1.0
        elif (
            self.numIters > 1e5
        ):  # Lower the exploration probability by a logarithmic factor.
            explorationProb = explorationProb / math.log(self.numIters - 100000 + 1)

        # ### START CODE HERE ###
        if explore:
            if np.random.rand() < self.explorationProb:
                return np.random.choice(self.actions)
            else:
                q_values = self.getQ(state, self.actions)
                return np.argmax(q_values)
        else:
            q_values = self.getQ(state, self.actions)
            return np.argmax(q_values)
        # ### END CODE HERE ###

    # Call this function to get the step size to update the weights.
    def getStepSize(self) -> float:
        return 0.005 * (0.99) ** (self.numIters / 500)

    # We will call this function with (s, a, r, s'), which you should use to update |weights|.
    # Note that if s is a terminal state, then terminal will be True.  Remember to check for this.
    # You should update W using self.getStepSize()
    def incorporateFeedback(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        nextState: np.ndarray,
        terminal: bool,
    ) -> None:
        # pass
        # ### START CODE HERE ###
        features = self.featureExtractor(state, action)
        q_value = self.getQ(state, action)
        if not terminal:
            next_q_values = self.getQ(nextState, self.actions)
            target_q_value = reward + self.discount * np.max(next_q_values)
        else:
            target_q_value = reward
        td_error = target_q_value - q_value
        update = self.getStepSize() * td_error * features
        self.W[:, action] += update
        # ### END CODE HERE ###


############################################################
# Problem 5c: Constrained Q-learning


class ConstrainedQLearning(FunctionApproxQLearning):
    def __init__(
        self,
        featureDim: int,
        featureExtractor: Callable,
        actions: List[int],
        discount: float,
        force: float,
        gravity: float,
        max_speed: Optional[float] = None,
        explorationProb=0.2,
    ):
        super().__init__(
            featureDim, featureExtractor, actions, discount, explorationProb
        )
        self.force = force
        self.gravity = gravity
        self.max_speed = max_speed

    # This algorithm will produce an action given a state.
    # Here we use the epsilon-greedy algorithm: with probability |explorationProb|, take a random action.
    # The input boolean |explore| indicates whether the RL algorithm is in train or test time. If it is false (test), we
    # should always choose the maximum Q-value action that is valid.
    def getAction(self, state: np.ndarray, explore: bool = True) -> int:
        if explore:
            self.numIters += 1
        explorationProb = self.explorationProb
        if self.numIters < 2e4:  # Always explore
            explorationProb = 1.0
        elif (
            self.numIters > 1e5
        ):  # Lower the exploration probability by a logarithmic factor.
            explorationProb = explorationProb / math.log(self.numIters - 100000 + 1)

        # ### START CODE HERE ###
        if random.random() < explorationProb:
            return random.choice(self.actions)
        else:
            # Find the action with the maximum Q-value
            max_action = max(self.actions, key=lambda a: self.getQ(state, a))
            return max_action
        # ### END CODE HERE ###


############################################################
# This is helper code for comparing the predicted optimal
# actions for 2 MDPs with varying max speed constraints
gym.register(
    id="CustomMountainCar-v0",
    entry_point="custom_mountain_car:CustomMountainCarEnv",
    max_episode_steps=1000,
    reward_threshold=-110.0,
)

mdp1 = ContinuousGymMDP("CustomMountainCar-v0", discount=0.999, timeLimit=1000)
mdp2 = ContinuousGymMDP("CustomMountainCar-v0", discount=0.999, timeLimit=1000)


# This is a helper function for 5c. This function runs
# ConstrainedQLearning, then simulates various trajectories through the MDP
# and compares the frequency of various optimal actions.
def compare_MDP_Strategies(mdp1: ContinuousGymMDP, mdp2: ContinuousGymMDP):
    rl1 = ConstrainedQLearning(
        36,
        lambda s, a: fourierFeatureExtractor(s, a, maxCoeff=5, scale=[1, 15]),
        mdp1.actions,
        mdp1.discount,
        mdp1.env.force,
        mdp1.env.gravity,
        10000,
        explorationProb=0.2,
    )
    rl2 = ConstrainedQLearning(
        36,
        lambda s, a: fourierFeatureExtractor(s, a, maxCoeff=5, scale=[1, 15]),
        mdp2.actions,
        mdp2.discount,
        mdp2.env.force,
        mdp2.env.gravity,
        0.065,
        explorationProb=0.2,
    )
    sampleKRLTrajectories(mdp1, rl1)
    sampleKRLTrajectories(mdp2, rl2)


def sampleKRLTrajectories(mdp: ContinuousGymMDP, rl: ConstrainedQLearning):
    accelerate_left, no_accelerate, accelerate_right = 0, 0, 0
    for n in range(100):
        traj = util.sample_RL_trajectory(mdp, rl)
        accelerate_left = traj.count(0)
        no_accelerate = traj.count(1)
        accelerate_right = traj.count(2)

    print(f"\nRL with MDP -> start state:{mdp.startState()}, max_speed:{rl.max_speed}")
    print(
        f"  *  total accelerate left actions: {accelerate_left}, total no acceleration actions: {no_accelerate}, total accelerate right actions: {accelerate_right}"
    )
