# !/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'NereWARin'

import Team
import util
import DataStoring as db
from Leagues import League, TeamResult
import Match as M
import values as v
from values import Coefficients as C, CUP_TYPE_ID
from operator import attrgetter, itemgetter
import random
import time
import os
import warnings
import copy

# c = Leagues.League("a", "a", [])
class Cup(League):
    """
    represents Cup, some methods from League were overridden
    """
    def __init__(self,
                 name = None, # id from Tournaments
                 season = None,
                 year = None,
                 members = None,
                 delta_coefs = C(v.VALUES_VERSION).getRatingUpdateCoefs("list"),
                 pair_mode = 1,
                 seeding = "A1_B16",
                 state_params = ("final_stage", ),
                 save_to_db = True,
                 prefix = "",
                 type_id = CUP_TYPE_ID, # id from tournaments_types_names
                 country_id = None):
        """

        :param name: id of tournament stored in db table
        :param season:

        # ACTUAL REVERSED ORDER !!!
        :param members: should be in seeding order (1place_team, 2place_team...) . net will ve provided by that class itself

        :param seeding: if Cup used as qualification for UEFA (or another special tournament),
        seeding must be a list in of dicts {int(round_number) : { "count" : int(seeded_teams), toss = "rnd" or "not_same_country_and_played_in_group" as in UEFA Champ League

        :param delta_coefs:
        :param pair_mode: 0 - one match in pair, 1 - home & guest but the final , 2 - always home & guest
        :return:
        """
        if prefix:
            if not isinstance(seeding, dict) and not isinstance(seeding, list):
                raise Exception, "seeding must be a list of dicts roundN:[seeded_teams], not %s" % type(seeding)
        else:
            if seeding not in self.getSeedings():
                raise Exception, "call independened Cup but seeding type not found in provided list getSeedings()"

        # kwargs = locals()
        # del kwargs["self"]
        # print "kwargs", kwargs, len(kwargs)
        # for a in kwargs: print a
        # super(Cup, self).__init__(**kwargs)
        super(Cup, self).__init__(**{par:val for par,val in locals().iteritems() if par != "self"}  )
        # super(Cup, self).__init__(name, season, year, members, delta_coefs, pair_mode, seeding, state_params, save_to_db,
        #                           prefix, type_id, country_id)
        self.pair_mode = pair_mode

        # self.results - empty list. after run() it will be filled as following:
        # [team_champion, team_finished_in_final, teams_finished_in_semi-final, ... , teams_finished_in_qualRoundn, ...
        # teams_finished_in_qualRound1# ]

        # print "\nWELCOME TO CUP ***", name, season, "***"

        state = {st:None for st in state_params}

        for member in self.members:
            self.results.append(TeamResult(member, state).get4table())
        # print "self.results", self.results
        # initialize net
        # self.seeding = copy.copy(seeding)
        self.seeding = seeding

        # {round: [ (t1,t2,pair_result, m1, m2) ... } , ... roundFinal : [ ... ]
        self.round_names = "not computed" # TODO make branch: get from params (if external scheme exists) OR compute in run()

        # self.net = {"not implemented yet" : None} # TODO net should be ini as start pos (1 round) and seeding (branch), then in run - updated from results
        # TODO its not necessacy for cups with
        self.net = {} #
        # *** HEART OF RUN METHOD TO RUN STEP-BY_STEP OR TO INITIALIZE NET BEFORE RUN***
        #   ***                 ***
        # CALL HELPER FUNCTIONS
        # if seeding == "rnd" or "A1_F16":
        # try:
        #     # print "teams_num", teams_num
        #     self.p_rounds, self.q_rounds = self.rounds_count(teams_num)#self.rounds_count(teams_num)
        #     # print "self.p_rounds %s, self.q_rounds %s" % (self.p_rounds, self.q_rounds)
        # except:
        #     print "%s. need more teams to run cup" % teams_num
        #     raise AttributeError
        # else:
        #     # convert number of round to round tournament (1/4, semi-final, etc.)
        #     self.round_names = self.roundNames(self.p_rounds, self.q_rounds)
        #     # print round_names
        #     all_rounds = self.p_rounds + self.q_rounds
        #
        #     pteamsI, qpairs = PQplaces(self.p_rounds, self.q_rounds)


    def __str__(self):
        string = ""
        for k, v in self.net.iteritems():
            roundname = self.round_names[k]
            string += str(roundname) + ":" + str(v) + "\n"
            # print "k", k
            # string += self.round_names[k] + ":" + str(v) + "\n"
        return string

    def getNet(self):
        """
        for print or display in web, has format
        self.net[round].append((pair[0].getName(), pair[1].getName(), results, looser TeamObj))
        where result can be (0:0) or ((1:1), (2:2)) - # TODO CHECK BY TEST

        :return:
        """
        return self.net

    def getSeedings(self):
        """
        seeding mode is by what rule pairs form
        return a tuple of the standart seeding behaviours, bur external scheme is allowed
        :return: available seeding modes supported by class
        """
        return (
            # BEST RATING vs WORST RATING. in every round first index of remaining teams vs last index of remaining teams
            # "David&Goliaf", - i broke it
            # first index of remaining teams - with random choice of the rest rem.teams
            "rnd",
            # hardcoded rule: winner of pair A1-B16 will play with winner of A16-B1 and etc.
            "A1_B16"
        )

    def rounds_count(self, teams_num):
        """
         define rounds count
        """
        if teams_num < 1:
            raise Exception, "no teams to run cup"
        if teams_num < 2:
            warnings.warn("RUN CUP %s FOR ONE TEAM %s") % (self.name, self.getMember(0).getName())
            return 0, 0
        # remaining teams number
        rem_tn = teams_num / 2.0

        # play-off rounds num
        p_rounds = 1
        while rem_tn >= 2:
            rem_tn = rem_tn / 2
            p_rounds += 1

        # qualification rounds num
        q_rounds = 0
        if rem_tn != 1.0:
            q_rounds += 1
        return p_rounds, q_rounds

    def roundNames(self, p_rounds, q_rounds):
        """
        generate round names to store and print
        (convert last round to final, last-1 to semifinal, etc.)
        :param p_rounds: number playoff rounds                  #!# starts from round 1
        :param q_rounds: numbers of qualification rounds        #!# starts from round 1
        :return:
        """
        rounds = p_rounds + q_rounds
        names = {}
        # print "we have %s rounds in Cup %s (%s in qualification, %s in playoff" % (rounds, self.getName(), q_rounds, p_rounds)

        names[rounds+1] = "Winner"
        names[rounds] = "Final"
        # names[rounds-1] = "Semi-Final"

        for round in range(q_rounds, rounds):
            names[round] = "1/%s-Final" % (2**(rounds-round))

        if q_rounds:
            names[q_rounds] = "Qualification Play-Off"
        for round in range(1, q_rounds):
            names[round] = "Qualification round %s" % round

        return names

    def run(self, print_matches = False):
        """
        generate matches, every match team rating and result updates
        after all, table updates and returns
        """

        # collecting match values to insert all matches of League to db at once
        self.match_values = []

        # register ID or tournament if unregistered yet
        if not self.prefix:
            # if unregistered yet - register now (for national Leagues)
            self.name_id = self.saveTounramentPlayed()
        # else (already registered) - so stored in self.id

        teams = list(self.getMember())
        teams_num = len(teams)
        # clear results
        self.results = {}
        self.net = {}

        # seeding "A1_B16"
        # 14-team cup example

        # play-off                                          *
        # round 1 (final)                   *                                 *
        # round 2 (semi-final)      *                *               *                 *
        # round 3 (1/4 final)    1     8         4      5         2      7         3      6
        # qualification
        # round 4 (qual 1)            8 9       4 13   5 12             7 10      3 14   6 11
        # // number = index in members + 1

        ####################### start helper functions block #######################
        def PQplaces(p_rounds, q_rounds):
            """
            p_rounds - number of play-off rounds in cup
            q_rounds - number of qualification rounds in cup

            return:
            qteams - number of teams played in qualification round, if q_rounds = 1
            pteam_num - number of teams witch start from playoff
            qpairs - number of pairs in qualification round
            """
            if  q_rounds > 1:
                raise NotImplemented, "for now it can be used only for national Cup that has at most 1 qual round "
                # for UEFA (that have custom schemas)  - we need not to use this method
            # teams in lowest play-off round
            pteam_num = 2 ** p_rounds
            # pais in highest qualification round
            qpairs = teams_num - pteam_num
            # indexes of teams that seeds directly in playoff
            borderI = pteam_num - qpairs
            qteams = qpairs * 2
            # return borderI, qpairs
            return -borderI

        def cupRound(self, _teams_, round, pair_mode, toss, print_matches = False):
            """
            teams - only those teams that will play in that round

            """
            # rem_teams = list(teams)
            teams = list(_teams_)
            loosers = []
            winners = []
             # it may be match or doublematch, so struggle is a common tournament for it
            struggles = len(teams)/2
            matches = struggles * (pair_mode + 1)

            # cause its Cup!
            playoff = True

            if pair_mode: # Two Matches in struggle
                classname = M.DoubleMatch
            else:
                classname = M.Match

            # create record of round
            self.net[round] = []

            for struggleN in range(struggles):

                if toss == "David&Goliaf":
                    # broke it 25.07.15
                    raise NotImplementedError
                    team1 = teams.pop(0) # favorite
                    team2 = teams.pop() # outsider
                elif toss == "rnd":
                    # TODO fix wild random! or at leat keep track of it to build self.net...
                    # TODO team0 will play with rnd team of the weak half

                    # random of weak half
                    # team1 = teams.pop(0) # favorite
                    # teams_num = len(teams)
                    # team2 = teams.pop(random.randrange(teams_num/2, teams_num)) # outsider

                    # full random
                    # for 1/4 Champions League
                    team1 = teams.pop(random.randrange(0, len(teams))) # favorite
                    team2 = teams.pop(random.randrange(0, len(teams))) # favorite

                elif toss == "A1_B16":
                    # print "check A1_B16 correctness - now its same as David&Goliaf - who lies?!!"
                    # answer: David&Goliaf lies as expected - we not need it mode
                    team1 = teams.pop(0) # favorite
                    team2 = teams.pop()

                elif toss == "not_same_country_and_played_in_group":
                    teams_num = len(teams)
                    half_len = teams_num / 2
                    # *** WARNING!
                    # here we might have first places of Group in the first half of list teams, 2nd places in 2nd half
                    # [H1, G1, F1, E1, D1, C1, B1, A1, A2, B2, C2, D2, E2, F2, G2]
                    # for 1/8 Champions League
                    t1_ind = random.randrange(half_len)             # 1 half
                    t2_ind = random.randrange(half_len, teams_num)  # 2 half
                    team1 = teams[t1_ind]
                    team2 = teams[t2_ind]

                    def played_in_group(t1_ind, t2_ind):
                        # while list has form
                        # we can only check indexes
                        half1_ind = t1_ind # % teams_num - no effect
                        half2_ind = t2_ind % teams_num

                        if half1_ind == (half_len - half2_ind - 1):
                            return True
                        return False
                        # columns = ["id_tournament", "round", "id_team1", "id_team2"]
                        # id_tournament = self.name
                        # round = "" # TODO  CONSISTS GROUP !!!!!
                        # values = [id_tournament, round, team1.getID(), team2.getID()]
                        # # TODO NOT IMPLEMENTED!
                        # # TODO SQL select id from %s where        db.MATCHES_TABLE
                        # warnings.warn("constraint for played_in_group not implemented!")
                        # return False

                    attempts = 100
                    while team1.getCountry() == team2.getCountry() or played_in_group(t1_ind, t2_ind):
                        team1 = teams[random.randrange(half_len)]  # 1 half
                        team2 = teams[random.randrange(half_len, teams_num)] # 2 half
                        attempts -= 1
                        if not attempts:
                            warnings.warn("cannot find opponent")
                            break
                    teams.remove(team1)
                    teams.remove(team2)

                else:
                    raise Exception, "unknown toss parameter %s" % toss


                pair = (team1, team2)
                if random.randint(0,1): # TODO if pair_mode < 1, need to compute what team played less matches at home
                    pair = (team2, team1)

                # p is a pair
                round_name = self.round_names[round]
                if struggles > 1:
                    # if more than one pair, enumerate pairs
                    round_name += " p%s" % (struggleN+1)

                # id_tournament = self.getID()
                # match_name = "%s %s. %s.%s"  \
                #                 % (self.getName(), self.season, round_name, struggleN)

                # PLAY MATCH OR DOUBLE_MATCH
                # struggle = classname(pair, self.delta_coefs, tournament=self.getID(), round = round_name, playoff = playoff, save_to_db=self.save_to_db"multi_values")
                struggle = classname(pair, self.delta_coefs, tournament=self.getID(), name = self.prefix + round_name,
                                     playoff = playoff, save_to_db="multi_values")
                struggle.run()
                # collecting match values to insert all matches of League to db at once
                self.match_values.append(struggle.get_insert_values())

                # print "classname %s" % classname
                results = struggle.getResult(1, 2, casted=True)
                looser = struggle.getLooser()
                # for res in results:
                #     print "res", res

                # TODO use ORM to draw net better
                # self.net[round].append((pair, results))
                self.net[round].append((pair[0].getName(), pair[1].getName(), results, looser))

                # print "results", results, [res for res in results]
                # print "result %s" % result
                if print_matches:
                    print struggle

                looser = struggle.getLooser()
                loosers.append(looser)

                winner = struggle.getWinner()
                winners.append(winner)

            # if print_matches:
            #    print "%s struggles (%s matches) were played" % (struggles, matches)

            return loosers, winners

        def RunRoundAndUpdate(self, round, pair_mode, results, teams, toss):
            # try:
            #
            # except:
            #     pass
            # round_name = self.getRoundNames()[round]

            # # create new list for pair in round
            # self.net[round] = []

            loosers, winners = cupRound(self, teams, round, pair_mode, toss, print_matches)

            # UPDATE RESULTS
            # TODO choose results form and net form
            # self.results.append(loosers)
            res = dict(results)
            res[round] = loosers

            # if print_matches:
            #     for stage, result in enumerate(self.results):
            #         print "results (loosers) of stage %s len of %s : %s" % (stage, len(self.results[stage]), [
            #             team.getName() for team in self.results[stage]])

            # return results, teams
            return res, loosers, winners

        def get_pairmode(round):
            """
            check if final round to switch to 1 match in pair
            """
            if round == self.all_rounds and self.pair_mode == 1:
                # print "switch pair_mode from 1 to 0 so it will be only one final match!"
                pairmode = 0 # ONE MATCH FOR FINAL
            else:
                pairmode = self.pair_mode
            return pairmode
        ####################### end helper functions block #######################

        # borderI - number of teams that skip first qualification round
        if isinstance(self.seeding, str):
            # national Cups
            self.p_rounds, self.q_rounds = self.rounds_count(teams_num)#self.rounds_count(teams_num)
            if not self.q_rounds:
                # if only play-off, all teams are seeded
                borderI = 0
            else:
                borderI = PQplaces(self.p_rounds, self.q_rounds)
            round_info = None
            toss = self.seeding
            # print "self.p_rounds %s, self.q_rounds %s" % (self.p_rounds, self.q_rounds)
            self.round_names = self.roundNames(self.p_rounds, self.q_rounds)

        elif isinstance(self.seeding, dict):
            # self.q_rounds = len(self.seeding)
            # self.p_rounds = 0
            self.q_rounds = 0
            self.p_rounds = len(self.seeding)
            round = 1
            round_info = self.seeding[round]
            # border is index started from what, seeded teams are get from self.members
            borderI = round_info["count"]
            if "toss" in round_info.keys():
                toss = round_info["toss"]
            else:
                toss = "A1_B16"

            if "qual" in self.prefix.lower():
                # for UEFA Qualification round_name like "Qualification 1"
                self.round_names = {round : self.prefix + str(round) for round in self.seeding.keys()}
            else:
                self.round_names = self.roundNames(self.p_rounds, self.q_rounds)
        else:
            raise ValueError, "unsupported argument type for seeding %s" %type(self.seeding)
        self.all_rounds = self.p_rounds + self.q_rounds

    # except:
    #     print "%s. need more teams to run cup" % teams_num
    #     raise AttributeError
    # else:
        # convert number of round to round tournament (1/4, semi-final, etc.)


        # print round_names

        winners = []

        # Qualification
        for round in range(1, self.all_rounds + 1):

            seeded = teams[-borderI:]
            # seeded = [self.getMember(i) for i in range(len(seeded))]
            _teams = seeded + winners
            pair_mode = get_pairmode(round)
            self.results, loosers, winners = RunRoundAndUpdate(self, round, pair_mode, self.results, _teams, toss)

            # if final round, break - cup complete!
            if round == self.all_rounds:
                break

            # update list of remaining teams
            for seeded_team in seeded:
                teams.remove(seeded_team)

            # prepare border for next round
            if round_info:
                next_round = round + 1
                round_info = self.seeding[next_round]
                borderI = round_info["count"]
                if "toss" in round_info.keys():
                    toss = round_info["toss"]
                else:
                    toss = "A1_B16"
            else:
                # national
                borderI = 0
                # after 1 round no more seeded teams, only winners of prev round
                # toss = self.seeding


        # assert len(teams) == 1, "Cup ends with more than one winner!"
        if not self.prefix:
            assert len(winners) == 1, "Cup ends with more than one winner!"
            self.winners = winners
        else:
            # for qualificaton for exampl9e
            self.winners = winners
        # print "self.winner" , self.winner

        # add team object to the top of the net
        # self.net[self.all_rounds+1] = (self.winners, )
        self.net[self.all_rounds+1] = [(winner.getName(), winner) for winner in self.winners]

        # # print result for EVERY round
        # if print_matches:
        #     for stage, result in enumerate(self.results):
        #         print "results (loosers) of stage %s len of %s : %s" % (stage, len(self.results[stage]), [team.getName() for team in self.results[stage]])

        self.saveToDB(self.net)
        return self.winners


    def saveToDB(self, net):
        """
        save Cup data to database
        :param: net is a dict round:[teams]
        """

        columns = db.select(table_names=db.TOURNAMENTS_RESULTS_TABLE, fetch="colnames", where = " LIMIT 0")[1:]
        # TODO edit getName to return readable info about tournament: readable name and season
        # print "\nsaving tournament %s results to database in columns %s" % (self.getName(), columns)
        multi_values = []
        for round, pairs_info in self.net.iteritems():

            # pos = self.prefix +
            if round in self.round_names.keys():
                pos = self.round_names[round] # TODO rename pos to final stage
            else:
                print "not round %s in self.round_names!" % round
                if self.prefix:
                    print "its ok, just break"
                    break
                else:
                    raise KeyError, "no name for round %s in self.net" % round
            if pos == "winner" and len(pairs_info) > 1:
                pos = "winners"
                # winners of sub-tournament not finish tournament - their results will be filled in next round
                # break
                print "multiple winners for round %s !!" #round
            for pair_info in pairs_info:
                id_team = pair_info[-1].getID()
                # id_team2 = pair_info[1].getName()
                values = [self.getID(), pos, id_team]
                multi_values.append(values)
                # db.insert(db.TOURNAMENTS_RESULTS_TABLE, columns, values)

        db.insert(db.TOURNAMENTS_RESULTS_TABLE, columns, multi_values)
        # print "inserted %s rows to %s"  % (len(multi_values), db.TOURNAMENTS_RESULTS_TABLE)

        # save matches results by one insert
        multi_values = []
        for struggle_values in self.match_values:
            for match_values in struggle_values:
                # print "match_values", match_values
                multi_values.append(match_values)
        # print  "Cup multi-values", multi_values
        columns = db.select(table_names=db.MATCHES_TABLE, fetch="colnames", suffix = " LIMIT 0")
        # print "Matches columns are ", columns
        columns = columns[1:] # (exclusive id) - its auto-incremented
        db.insert(db.MATCHES_TABLE, columns, multi_values)
        # print "Cups: inserted %s matches" % len(multi_values)


    def getRoundNames(self):
        return self.round_names

    def getWinner(self):
        return self.winners

    def test(self, print_matches = False, print_ratings = False,
             pre_truncate = False, post_truncate = False):
        """
        test Cup and print info
        """

        print "\nTEST CUP CLASS\n"
        print "pair_mode = %s\nseeding = %s\nmembers_num = %s\n" % (self.pair_mode, self.seeding, len(self.getMember()))
        print "initial Net:"
        print self#.printTable()
        if print_matches:
            print "\nMatches:"
        self.run(print_matches)
        print "\nWinner:\n%s" % [winner.getName() for winner in self.getWinner()]
        # print "\nresults:\n%s" % [(k, [team.getName() for team in self.results[k]] ) for k in self.results.keys()]
        print "\nresults:"
        # for k in self.results.keys():
        #     # TODO sort results by round (maybe store them in list)
        #     print k, [team.getName() for team in self.results[k]]
        print self
        print "\nFinal Net:\n", str(self), "\n"

        if print_ratings:
            for team in self.getMember():
                print team.getName(), team.getRating()




@util.timer
def Test(*args, **kwargs):
    """
    Test Cup

    :param args:
    :param kwargs: test arguments are listed below

    by default, save_db = True,  team_num = 20, all other options are disabled

    :return:
    """
    print "Cups.Test() with args", args, kwargs

    # used by clearing inserted rows by test after it runs
    last_m_row = db.trySQLquery(query="SELECT id FROM %s ORDER BY ID DESC LIMIT 1"
                                      % db.MATCHES_TABLE, fetch="one")
    last_tp_row = db.trySQLquery(query="SELECT id FROM %s ORDER BY ID DESC LIMIT 1"
                                       % db.TOURNAMENTS_PLAYED_TABLE, fetch="one")
    last_tr_row = db.trySQLquery(query="SELECT id FROM %s ORDER BY ID DESC LIMIT 1"
                                       % db.TOURNAMENTS_RESULTS_TABLE, fetch="one")
    print "last rows before Cup test are: last_m_row %s, last_tp_row %s, last_tr_row %s " % \
          ( last_m_row, last_tp_row, last_tr_row    )

    # VERSION = "v1.1"
    with open(os.path.join("", 'VERSION')) as version_file:
        values_version = version_file.read().strip()
    coefs = C(values_version).getRatingUpdateCoefs("list")

    teams = []
    if "team_num" in kwargs.keys():
        team_num = kwargs["team_num"]
    else:
        # default
        team_num = 20

    if "seedings" in kwargs.keys():
        seedings = kwargs["team_num"]
    else:
        # default
        s =  Cup("no Cup, just getSeedings", "season", [], coefs)
        seedings = s.getSeedings()

    if "print_matches" in kwargs.keys():
        print_matches = kwargs["print_matches"]
    else:
        # default
        print_matches = True

    if "print_ratings" in kwargs.keys():
        print_ratings = kwargs["print_ratings"]
    else:
        # default
        print_ratings = False

    if "pair_mode" in kwargs.keys():
        pair_modes = kwargs["pair_mode"]
        if isinstance(pair_modes, int):
            pair_modes = (pair_modes, )
    else:
        # default
        pair_modes = (0,1,2)

    if "save_to_db" in kwargs.keys():
        save_to_db = kwargs["save_to_db"]
    else:
        # default
        save_to_db = True

    if "pre_truncate" in kwargs.keys():
        pre_truncate = kwargs["pre_truncate"]
    else:
        # default
        pre_truncate = False

    if "post_truncate" in kwargs.keys():
        post_truncate = kwargs["post_truncate"]
    else:
        # default
        post_truncate = False


    if pre_truncate:
        print "pre_truncate!"
        db.truncate(db.TOURNAMENTS_PLAYED_TABLE)
        db.truncate(db.TOURNAMENTS_RESULTS_TABLE)
        db.truncate(db.MATCHES_TABLE)


    for i in range(team_num):
        teamN = i + 1
        # # old-styled
        # rating = team_num - i
        # uefa_pos = teamN
        # teams.append(Team.Team("FC team%s" % teamN, "RUS", rating, "Команда%s" % teamN, uefa_pos))
        # new-styled
        teams.append(Team.Team(teamN))
        # teams.append(Team.Team(name=teamN, country="RUS", rating=teamN*10.0, uefaPos=teamN, countryID=(teamN*10)%52))

    # TEST CUP CLASS
    # for seeding in Cup.getSeedings(Cup):
    #     print seeding
    for pair_mode in pair_modes:
        # pair_mode = 0 # one match
        # pair_mode = 1 # home + guest every match but the final
        # pair_mode = 2 # home + guest every match
        for seeding in seedings:
            # print "TEST CUP: seeding=%s, pair_mode=%s" %(seeding, pair_mode)
            # print "teams, coefs, pair_mode, seeding", teams, coefs, pair_mode, seeding
            # old-styled
            # tstcp = Cup("testCup", "2015/2016", teams, coefs, pair_mode, seeding)
            # new-styled
            season, year = 1, db.START_SEASON
            Cup(name=v.TEST_CUP_ID, season=season, year=year, members=teams, delta_coefs= coefs, pair_mode=pair_mode,
                        seeding=seeding, save_to_db=save_to_db)\
                .test(print_matches, print_ratings)

    if post_truncate:
        db.truncate(db.TOURNAMENTS_PLAYED_TABLE)
        db.truncate(db.TOURNAMENTS_RESULTS_TABLE)
        db.truncate(db.MATCHES_TABLE)



# TEST
if __name__ == "__main__":


    # PRINT MATCHES AFTER RUN
    PRINT_MATCHES = False
    PRINT_MATCHES = True
    # PRINT RATINGS AFTER RUN
    PRINT_RATINGS = False
    # PRINT_RATINGS = True
    # RESET ALL MATCHES DATA BEFORE TEST
    PRE_TRUNCATE = False
    PRE_TRUNCATE = True
    # RESET ALL MATCHES DATA AFTER TEST
    POST_TRUNCATE = False
    # POST_TRUNCATE = True
    # SAVE TO DB - to avoid data integrity (if important data in table exists), turn it off
    SAVE_TO_DB = False
    SAVE_TO_DB = True
    Test("Cup", team_num = 20, pre_truncate = PRE_TRUNCATE, post_truncate = POST_TRUNCATE, save_to_db = SAVE_TO_DB,
         print_matches = PRINT_MATCHES, print_ratings=PRINT_RATINGS)