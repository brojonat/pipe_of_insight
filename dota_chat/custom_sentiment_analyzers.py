import sys,os,pdb,glob,shutil

import numpy as np 
import pandas as pd

from nltk.sentiment.vader import SentimentIntensityAnalyzer


class DefaultCustomAnalyzer(SentimentIntensityAnalyzer):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def update_hardcoded_dota_sentiments(self):

        # define the new lexicon entries
        new_words = {
            # bad
            'ff': -2.,
            'finish': -1.,
            'fast': -1.,
            'fats': -1.,
            'end': -1.,
            'fuk': -2.,
            'meirde': -2.,
            'reddit': -1.,
            'cyka': -2.,
            'blyat': -2.,
            'byat': -2.,
            'afk': -1.,
            'injoker': -1.,

            # good
            'turtle': 1.,
            'ggwp': 2.,
            'pog': 1.,
            'pogchamp': 1.,
            'poggers': 1.,

            }

        # update
        self.lexicon.update(new_words)

        return 0
