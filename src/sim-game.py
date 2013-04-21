#!/usr/bin/python
import logging
import random
from collections import namedtuple

logging.basicConfig(level=logging.INFO,
                    format=('%(asctime)s [%(levelname)s] '
                            '%(pathname)s:%(lineno)5d.. %(message)s'))

# ============== Utility functions ==================
def Average(number, times):
  return number / float(times)

def Winner(a, b):
  if a > b:
    return 'A'
  elif a < b:
    return 'B'
  else:
    return 'Draw'

def GetChance(prob):
  assert prob <= 1 and prob >= 0, 'prob %d is not valid' % prob
  return random.random() < prob

def GetTheOtherTeam(name):
  the_other_team = {'A':'B', 'B':'A'}
  return the_other_team[name]

def ShotType2Pts(shot_type):
  mapping = {'two_pts': 2, 'three_pts': 3}
  return mapping[shot_type]

# Record the ability of a Team
Ability = namedtuple('Ability', ['shot_pct', 'offensive_reb_pct'])
ShotPct = namedtuple('ShotPct', ['ft', 'two_pts', 'three_pts'])
Strategy = namedtuple('Strategy', ['shot_selection'])
ShotSelection = namedtuple('ShotSelection', ['two_pts', 'three_pts'])
TeamConfig = namedtuple('TeamConfig', ['ability', 'strategy'])
SimulationConfig = namedtuple('SimulationConfig',
                              ['possessions_per_game', 'play_games'])


# =============== Default settings ===================
# Assume the total possessions of a game to be fixed.
POSSESSION_PER_GAME = 200
# Number of simulated games.
PLAY_GAMES = 1000
DEFAULT_SIMULATION_CONFIG = SimulationConfig(
    possessions_per_game=POSSESSION_PER_GAME,
    play_games=PLAY_GAMES)

# This team only shoots 3-ball
ABILITY_A = Ability(
    shot_pct=ShotPct(ft=1.0, two_pts=0.405, three_pts=0.27),
    offensive_reb_pct=0.24)
STRATEGY_A = Strategy(shot_selection=ShotSelection(
    two_pts=0.0, three_pts=1.0))

# This team does not like 3-ball
ABILITY_B = Ability(
    shot_pct=ShotPct( ft=1.0, two_pts=0.405, three_pts=0.27),
    offensive_reb_pct=0.24)
STRATEGY_B = Strategy(shot_selection=ShotSelection(
    two_pts=1.0, three_pts=0.0))

DEFAULT_TEAM_CONFIGS = {"A": TeamConfig(ability=ABILITY_A, strategy=STRATEGY_A),
                        "B": TeamConfig(ability=ABILITY_B, strategy=STRATEGY_B)}


class Team(object):
  """Class to represent a team. Properties are self-explained."""
  def __init__(self, name, team_config):
    self._ability, self._strategy = team_config
    self._name = name

    # For one-game statistics
    self.pts = 0

    # For multiple games statistics
    self.wins = 0
    self.total_pts = 0
    self.total_fga = 0
    self.total_fgm = 0
    self.total_reb = 0

  def Shot(self):
    # Shoot a ball
    self.total_fga += 1

    shot_type_is_two_pts = GetChance(self._strategy.shot_selection.two_pts)
    shot_type = 'two_pts' if shot_type_is_two_pts else 'three_pts'
    goal = GetChance(getattr(self._ability.shot_pct, shot_type))
    if goal:
      self.Goal(ShotType2Pts(shot_type))
    else:
      logging.debug('%s missed a %s', self._name, shot_type)
    return goal

  def FightForOffensiveRebound(self, defensive_team):
    get_offensive_rebound = GetChance(self._ability.offensive_reb_pct)
    if get_offensive_rebound:
      self.GetRebound()
    else:
      defensive_team.GetRebound()
    return get_offensive_rebound

  def Goal(self, pts):
    logging.debug('%s scores +%d', self._name, pts)
    self.pts += pts
    self.total_pts += pts
    self.total_fgm += 1

  def GetRebound(self):
    logging.debug('%s rebound +1', self._name)
    self.total_reb += 1

  def NewGame(self):
    self.pts = 0

  def WinAGame(self):
    self.wins += 1



class Simulation(object):
  def __init__(self, simulation_config=DEFAULT_SIMULATION_CONFIG,
               team_configs=DEFAULT_TEAM_CONFIGS):
    self._possessions_per_game = simulation_config.possessions_per_game
    self._play_games = simulation_config.play_games
    self._team_configs = team_configs
    self._teams = {"A": Team(name="A", team_config=team_configs["A"]),
                   "B": Team(name="B", team_config=team_configs["B"])}

  def RunAll(self):
    for game in xrange(self._play_games):
      self._RunOneGame()

  def _NewGame(self):
    self._teams["A"].NewGame()
    self._teams["B"].NewGame()

  def _JumpBall(self):
    return "A" if GetChance(0.5) else "B"

  def _EndsGame(self):
    winner = Winner(self._teams["A"].pts, self._teams["B"].pts)
    if winner == "A" or winner == "B":
      self._teams[winner].WinAGame()
    logging.debug("%d:%d, winner: %s",self._teams["A"].pts,
                  self._teams["B"].pts, winner)


  def _RunOnePossession(self, offensive_team):
    "Run one possession and returns next offensive team."
    defensive_team = GetTheOtherTeam(offensive_team)

    # Offsive team shoots.
    goal = self._teams[offensive_team].Shot()

    # Goals, change side. End of one possession.
    if goal:
      return defensive_team

    # Missed.
    else:

      # Fights for offensive rebound.
      get_off_rebound = self._teams[offensive_team].FightForOffensiveRebound(
          self._teams[defensive_team])

      # Gets offensive rebound, tries again. End of one possession.
      if get_off_rebound:
        return offensive_team

      # The other team gets defensive rebound.
      else:
	return defensive_team

  def _RunOneGame(self):
    # New game !
    self._NewGame()

    # Jump ball !
    offensive_team = self._JumpBall()
    logging.debug('Jump ball result: offensive team is %s', offensive_team)
    # Play a game with total_possession.
    for pos in xrange(self._possessions_per_game):
      offensive_team = self._RunOnePossession(offensive_team=offensive_team)
      logging.debug("%d : %d", self._teams["A"].pts, self._teams["B"].pts)

    # Game ends.
    self._EndsGame()

  def _ShowAverageCompare(self, display_item, item):
    return "average %s: %.2f : %.2f" % (display_item,
        Average(getattr(self._teams["A"], item), self._play_games),
        Average(getattr(self._teams["B"], item), self._play_games))

  def PrintResult(self):
    logging.info("=====Show statistics after %d games.=====", self._play_games)

    logging.info('\n'.join(['\n%s setting\n%s\n' % (k, v)
                           for k, v in self._team_configs.iteritems()]))
    logging.info(self._ShowAverageCompare('win', 'wins'))
    logging.info(self._ShowAverageCompare('pts', 'total_pts'))
    logging.info(self._ShowAverageCompare('fga', 'total_fga'))
    logging.info(self._ShowAverageCompare('fgm', 'total_fgm'))
    logging.info("average fg_pct: %.2f%% : %.2f%%",
        self._teams["A"].total_fgm / float(self._teams["A"].total_fga) * 100,
        self._teams["B"].total_fgm / float(self._teams["B"].total_fga) * 100)
    logging.info(self._ShowAverageCompare('reb', 'total_reb'))


#TODO, add yaml parser to read setting from input
class SimulationConfigurator(object):
  def __init__(self):
    self._simulation_config = None
    self._team_configs = None

  def GetSimulationConfig(self):
    raise NotImplementedError

  def GetTeamConfigs(self):
    raise NotImplementedError


def main():
  #TODO, add yaml parser to read setting from input
  #sim_configurator = SimulationConfigurator()
  #simulation = Simulation(sim_configurator.GetSimulationConfig(),
  #                        sim_configurator.GetTeamConfigs())
  simulation = Simulation()
  simulation.RunAll()
  simulation.PrintResult()


if __name__ == "__main__":
  main()
