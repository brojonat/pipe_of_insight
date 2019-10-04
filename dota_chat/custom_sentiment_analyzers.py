import sys,os,pdb,glob,shutil

import numpy as np 
import pandas as pd

from nltk.sentiment.vader import SentimentIntensityAnalyzer


class DefaultCustomAnalyzer(SentimentIntensityAnalyzer):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def update_hardcoded_dota_sentiments(self):

        # define the new lexicon entries
        new_lex = {
            # examples of negative sentiment in dota lexicon
            'ff': -2.,
            'finish': -1.,
            'fast': -1.,
            'fats': -1.,
            'end': -1.,
            'meirde': -2.,
            'reddit': -1.,
            'cyka': -2.,
            'afk': -1.,

            # examples of positive sentiment in dota lexicon
            'turtle': 1.,
            'ggwp': 2.,
            'glhf':2.,
            'gl':2.,
            'hf':2.,
            'commend':2.,
            'commended':2.,
            }

        # update
        self.lexicon.update(new_lex)

        return 0
