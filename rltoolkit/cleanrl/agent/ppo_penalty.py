from typing import Dict, List, Optional, Tuple, Union

import gymnasium as gym
import numpy as np
import torch
from rltoolkit.cleanrl.agent.base import BaseAgent
from rltoolkit.cleanrl.rl_args import PPOArguments
from rltoolkit.cleanrl.utils.pg_net import ActorCriticNet
from rltoolkit.data.utils.type_aliases import RolloutBufferSamples
from torch.distributions import Categorical


class PPOPenaltyAgent(BaseAgent):
    """Proximal Policy Optimization (PPO) Agent.

    The agent interacts with the environment using an actor-critic model.
    The actor updates the policy distribution based on the critic's feedback.

    Args:
        args (PPOArguments): Configuration arguments for PPO.
        env (gym.Env): Environment to interact with.
        state_shape (Union[int, List[int]]): Shape of the state space.
        action_shape (Union[int, List[int]]): Shape of the action space.
        device (Optional[Union[str, torch.device]]): Device for computations.
    """

    def __init__(
        self,
        args: PPOArguments,
        env: gym.Env,
        state_shape: Union[int, List[int]],
        action_shape: Union[int, List[int]],
        device: Optional[Union[str, torch.device]] = None,
    ) -> None:
        self.args = args
        self.env = env
        self.obs_dim = int(np.prod(state_shape))
        self.action_dim = int(np.prod(action_shape))
        self.learner_update_step = 0
        self.device = device if device is not None else torch.device('cpu')

        # Initialize actor and critic networks
        self.actor_critic = ActorCriticNet(self.obs_dim, self.args.hidden_dim,
                                           self.action_dim).to(self.device)

        # All Parameters
        self.all_parameters = self.actor_critic.parameters()

        # Optimizer
        self.optimizer = torch.optim.Adam(self.all_parameters,
                                          lr=self.args.learning_rate,
                                          eps=self.args.epsilon)

    def get_action(self, obs: np.ndarray) -> Tuple[float, int, float, float]:
        """Sample an action from the policy given an observation.

        Args:
            obs (np.ndarray): The observation from the environment.

        Returns:
            Tuple[float, int, float, float]: A tuple containing:
                - value (float): The value estimate from the critic.
                - action (int): The sampled action.
                - log_prob (float): The log probability of the sampled action.
                - entropy (float): The entropy of the action distribution.
        """
        obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(self.device)
        value = self.actor_critic.get_value(obs_tensor)
        logits = self.actor_critic.get_action(obs_tensor)
        dist = Categorical(logits=logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        entropy = dist.entropy()
        return value.item(), action.item(), log_prob.item(), entropy

    def get_value(self, obs: np.ndarray) -> float:
        """Use the critic model to predict the value of an observation.

        Args:
            obs (np.ndarray): The observation from the environment.

        Returns:
            float: The predicted value of the observation.
        """
        obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(self.device)
        value = self.actor_critic.get_value(obs_tensor)
        return value.item()

    def predict(self, obs: np.ndarray) -> int:
        """Predict the action with the highest probability given an
        observation.

        Args:
            obs (np.ndarray): The observation from the environment.

        Returns:
            int: The predicted action.
        """
        obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.actor_critic.get_action(obs_tensor)
            dist = Categorical(logits=logits)
            action = dist.probs.argmax(dim=1, keepdim=True)
        return action.item()

    def learn(self, batch: RolloutBufferSamples) -> Dict[str, float]:
        """Update the model using a batch of sampled experiences.

        Args:
            batch (RolloutBufferSamples): A batch of sampled experiences.
            RolloutBufferSamples contains the following fields:
            - obs (torch.Tensor): The observations from the environment.
            - actions (torch.Tensor): The actions taken by the agent.
            - old_values (torch.Tensor): The value estimates from the critic.
            - old_log_prob (torch.Tensor): The log probabilities of the actions.
            - advantages (torch.Tensor): The advantages of the actions.
            - returns (torch.Tensor): The returns from the environment.

        Returns:
            Dict[str, float]: A dictionary containing the following metrics:
            - value_loss (float): The value loss of the critic.
            - actor_loss (float): The actor loss of the policy.
            - entropy_loss (float): The entropy loss of the policy.
            - approx_kl (float): The approximate KL divergence.
            - clipped_frac (float): The fraction of clipped actions.
        """
        obs = batch.obs
        actions = batch.actions
        old_values = batch.old_values
        old_log_probs = batch.old_log_prob
        advantages = batch.advantages
        returns = batch.returns

        # Compute new values, log probs, and entropy
        new_values = self.actor_critic.get_value(obs)
        logits = self.actor_critic.get_action(obs)
        dist = Categorical(logits=logits)
        new_log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        # Compute entropy loss
        entropy_loss = entropy.mean()

        # Normalize advantages
        if self.args.norm_advantages:
            advantages = (advantages - advantages.mean()) / (
                advantages.std() + 1e-8).to(self.device)

        # Compute actor loss
        log_ratio = new_log_probs - old_log_probs
        ratio = torch.exp(log_ratio)
        surr1 = ratio * advantages
        surr2 = (torch.clamp(ratio, 1.0 - self.args.clip_param,
                             1.0 + self.args.clip_param) * advantages)
        actor_loss = -(torch.min(surr1, surr2)).mean()

        # Compute value loss
        if self.args.clip_vloss:
            value_pred_clipped = old_values + torch.clamp(
                new_values - old_values, -self.args.clip_param,
                self.args.clip_param)
            value_losses_unclipped = (new_values - returns).pow(2)
            value_losses_clipped = (value_pred_clipped - returns).pow(2)
            value_loss = (
                0.5 *
                torch.max(value_losses_unclipped, value_losses_clipped).mean())
        else:
            value_loss = 0.5 * (new_values - returns).pow(2).mean()

        # Total loss
        loss = (actor_loss + value_loss * self.args.value_loss_coef -
                entropy_loss * self.args.entropy_coef)

        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        if self.args.max_grad_norm is not None:
            torch.nn.utils.clip_grad_norm_(self.all_parameters,
                                           self.args.max_grad_norm)
        self.optimizer.step()
        self.learner_update_step += 1

        # Calculate KL divergence metrics
        with torch.no_grad():
            clipped = ratio.gt(1 + self.args.clip_param) | ratio.lt(
                1 - self.args.clip_param)
            approx_kl = (-log_ratio).mean()
            clipped_frac = torch.as_tensor(clipped, dtype=torch.float32).mean()

        return {
            'loss': loss.item(),
            'value_loss': value_loss.item(),
            'actor_loss': actor_loss.item(),
            'entropy_loss': entropy_loss.item(),
            'approx_kl': approx_kl.item(),
            'clipped_frac': clipped_frac.item(),
        }
