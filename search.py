# -*- coding: utf-8 -*-
"""
Created on Thu Aug  1 13:28:46 2019

@author: admin
"""


import json
import os
import numpy as np
import pandas as pd
from collections import Counter
from datetime import datetime
import time


class FbAnalyzer:
    def __init__(self, filepath):
        with open(filepath) as json_file:
            data = json.load(json_file)
        data_dict = self.decode(json.dumps(data))
        self.data_dict = json.loads(data_dict)
        self.df = pd.DataFrame(self.data_dict['messages'])
        self.df['content'] = self.df['content'].apply(self.decode)
        self.members = [self.decode(member['name']) for member in self.data_dict['participants']]
        self.df['sender_name'] = self.df['sender_name'].apply(self.decode)
        self.all_members = self.df['sender_name'].unique().tolist()

    @staticmethod
    def decode(string):
        """decode string to utf-8"""
        if isinstance(string, str):
            return string.encode('iso-8859-1').decode('utf-8')
        else:
            return string


    def get_statistics(self):
        """
        Get message statistics for every member

        Returns
        -------
        DataFrame
            DataFrame with counted messages of every type for every member.

        """
        self.statistics = pd.DataFrame(index=self.all_members)
        total = pd.DataFrame(self.df.groupby(['sender_name']).size(), columns=['total'])
        subcols = ['content', 'photos', 'gifs', 'share', 'audio_files', 'sticker', 'plan', 'files', 'videos']
        cols = [total]
        for subcol in subcols:
            cols.append(pd.DataFrame(df.dropna(subset=[subcol]).groupby(['sender_name']).size(), columns=[subcol]))
        self.statistics = pd.concat(cols, axis=1).fillna(0)
        return self.statistics


    def count_words(self, words):
        """
        Count occurencies of given words for every member

        Parameters
        ----------
        words : list
            list of words. E.g. ['apple', 'banana'].

        Returns
        -------
        member_words_counter : dict
            number of occurencies for every member.

        """
        member_words_counter = {}
        words = [word.lower() for word in words]
        for member in self.all_members:
            member_words_counter[member] = 0
            messages = df[df.sender_name==member]['content'].dropna()
            for message in messages:
                for word in words:
                    if word in message.lower():
                        member_words_counter[member] += 1
        return member_words_counter


    def get_most_reacted_messages(self, content_type, min_reactions):
        """
        Get most reacted messages

        Parameters
        ----------
        content_type : str
            type of message. one of following:
                content, photos, gifs, share, audio_files, sticker, plan, files, videos
    .
        min_reactions : int
            minimum reactions that message got.

        Returns
        -------
        reacted_messages : DataFrame
            DataFrame with data.

        """
        reacted_messages = df[df.reactions.notnull()][['sender_name', 'timestamp_ms', content_type, 'reactions']]
        reacted_messages = reacted_messages[reacted_messages[content_type].notnull()]
        if reacted_messages.shape[0] == 0:
            return reacted_messages
        reacted_messages['len_reactions'] = reacted_messages.apply(lambda row: len(row.reactions), axis = 1)
        reacted_messages['time'] = reacted_messages.apply(lambda row: datetime.fromtimestamp(round(row.timestamp_ms/1000)), axis=1)
        reacted_messages = reacted_messages[reacted_messages.len_reactions >= min_reactions].drop(columns=['reactions', 'timestamp_ms'])
        return reacted_messages



    def get_messages_by_day(self):
        """
        returns dataframe with messages summed by day
        """
        df_day = pd.Series(data=self.df['timestamp_ms'])
        df_day = df_day.dt.floor('D')
        df_day = df_day.value_counts()
        df_day = df_day.rename_axis('date')
        df_day = df_day.reset_index(name='messages')
        df_day = df_day.sort_values(by=['date'])
        return df_day
    
    
    def plot_by_day(self):
        """
        plot chart for messages per day
        """
        df_day = pd.Series(data=pd.to_datetime(df['timestamp_ms'], unit='ms'))
        df_day = df_day.dt.floor('D')
        df_day = df_day.value_counts()
        df_day = df_day.rename_axis('date')
        df_day = df_day.reset_index(name='messages')
        df_day = df_day.sort_values(by=['date'])
        df_day[['date','messages']].plot(
                'date',
                legend=True,
                figsize=(15,10),
                title='Total messages per day',
                )


    def most_common_words(self, min_chacters, number_of_returned_words):
        """
        

        Parameters
        ----------
        min_chacters : int
            minimum length of word to be counted.
        number_of_returned_words : int
            number of words to return.

        Returns
        -------
        most_com : list
            list of tuples in format:
            [(word, count), (word2, count), ...]

        """

        c = self.df['content'].str.cat(sep=';')
        c = self.decode(c)
        c = c.replace(' ', ';')
        c = c.replace(',', '')
        c = c.replace('!', '')
        c = c.replace('?', '')
        c = c.replace('.', '')
        c = c.split(';')
        c = pd.DataFrame(c, columns=['text'])
        c['len'] = c.text.str.len()
        c = c[c.len >= min_chacters]
        most_com = Counter(c['text'].str.lower())
        most_com = most_com.most_common(number_of_returned_words)
        return most_com


    def get_members_stats_monthly(self):
        """
        Get dataframe with number of
        messages sent by every member
        in every month

        Returns
        -------
        df_monthly : DataFrame
            DataFrame with counted messages.

        """
        df_stats = pd.DataFrame(self.df, copy=True)
        df_stats = df_stats.drop(columns=['type'])
        df_stats['timestamp_ms'] = pd.to_datetime(df_stats['timestamp_ms'], unit='ms')
        df_stats['timestamp_ms'] = df_stats.timestamp_ms.dt.to_period('M')
        df_stats = df_stats.groupby(by=['timestamp_ms', 'sender_name']).count()
        df_stats = df_stats.loc[:].sum(axis=1)
        df_stats = pd.DataFrame(df_stats)
        df_stats.columns = ['Messages']
        df_stats = df_stats.reset_index(level=['timestamp_ms', 'sender_name'])
        df_stats.columns = ['Month', 'User', 'Messages']
    
        #create final dataframe
        df_monthly = pd.DataFrame()
        months = np.arange(min(df_stats['Month']),
                           max(df_stats['Month'])+1,
                           dtype='datetime64[M]')
        df_monthly['Month'] = months
        df_monthly['Month'] = df_monthly.Month.dt.to_period('M')
    
        #add data for every user
        users = df_stats.User.unique()
        for user in users:
            df_temp = df_stats[df_stats['User']==user]
            df_temp = df_temp.drop(columns=['User'])
            df_temp.columns = ['Month', user]
            df_monthly = df_monthly.merge(df_temp, on='Month')
        df_monthly['Total']= df_monthly.sum(axis=1, numeric_only=True)
        df_monthly = df_monthly.fillna(0)
        return df_monthly


    def plot_by_month_members(self, without_total=True, logaritmic=True):
        """
        Plot chart for messages per month
        for every user

        Parameters
        ----------
        without_total : bool, optional
            whether draw line fot total messages. The default is True.
        logaritmic : bool, optional
            whether y axis should be logaritmic. The default is True.

        Returns
        -------
        None.

        """
        df_monthly = self.get_members_stats_monthly()
        xticks = np.arange(min(df_monthly['Month']),
                         max(df_monthly['Month'])+1,
                         dtype='datetime64[M]')
        if without_total == True:
            df_monthly = df_monthly.drop(columns='Total')
        df_monthly.plot(
                x='Month',
                legend=True,
                figsize=(15,10),
                title='Messages per month',
                xticks=xticks,
                logy=logaritmic
                )
    
    
    def plot_by_month_total(self, logaritmic=True):
        """
        Plot chart for messages per month
        only total

        Parameters
        ----------
        logaritmic : bool, optional
            whether y axis should be logaritmic. The default is True.

        Returns
        -------
        None.

        """
        df_monthly = self.get_members_stats_monthly()
        xticks=np.arange(min(df_monthly['Month']),
                         max(df_monthly['Month'])+1,
                         dtype='datetime64[M]')
        df_monthly[['Month', 'Total']].plot(
                x='Month',
                legend=True,
                figsize=(15, 10),
                title='Messages per month',
                xticks=xticks,
                logy=logaritmic
                )


    def number_of_reactions_for_members(self):
        """
        Get DataFrame with number of every reaction for every member

        Returns
        -------
        df_mem_react : DataFrame
            DataFrame with number of every reaction for every member. Columns are reactions, rows are members.

        """
        c = self.df.loc[~pd.isnull(df.reactions)]['reactions'] #get only reactions
        #convert to dataframe with as many columns as max reactions
        #to one message
        d = pd.DataFrame.from_dict(c.array)
        #get working dataframe
        df_reactions = pd.Series(d.values.ravel('F')).dropna()
        df_reactions = pd.DataFrame.from_records(df_reactions)
        df_reactions['reaction'] = df_reactions['reaction'].apply(self.decode)
        actors = df_reactions.actor.unique()
        reactions = df_reactions.reaction.unique()
    
        #get final dataframe
        df_mem_react = pd.DataFrame(columns=reactions)
        for actor in actors:
            df_temp = df_reactions[df_reactions['actor']==actor]
            df_temp = df_temp.groupby('reaction').count()
            actor = self.decode(actor)
            df_temp.columns=[actor]
            df_mem_react = df_mem_react.append(df_temp[actor])
        df_mem_react.index.names = ['Member']
        df_mem_react['Total']= df_mem_react.sum(axis=1, numeric_only=True)
        return df_mem_react

    def plot_number_of_reactions_for_member(self):
        """
        Draw bar chart containing number of reactions for every member.

        Returns
        -------
        None.

        """

        df_mem_react = self.number_of_reactions_for_members()
        df_for_plot = df_mem_react.drop(columns='Total')
        ax = df_for_plot.plot.bar(
            legend=True,
            figsize=(10, 12),
            title='Reactions per member',
            subplots=False,
            logy=False,
            stacked=True,
            table=False,
            rot=0,
            )
        ax.set_ylabel('Number')
        ax.set_xlabel('\nMember')

    def plot_number_of_reactions(self):
        """
        Draw bar chart containing total number of reactions.

        Returns
        -------
        None.

        """
        df_mem_react = self.number_of_reactions_for_members()
        total_reactions = df_mem_react.sum()
        total_reactions = total_reactions.drop('Total')
        ax = total_reactions.plot.bar(
            legend=False,
            figsize=(15, 10),
            title='Count of every reaction',
            rot=0,
            )
        ax.set_ylabel('Count')
        ax.set_xlabel('\nReaction')
    
    
    def plot_messages_by_hour(self):
        """
        Bar chart for total messages sent in every hour

        Returns
        -------
        None.

        """
        df_stats = df['timestamp_ms']
        df_stats = pd.to_datetime(df_stats, unit='ms')
        df_stats = df_stats.dt.hour
        df_stats = df_stats.value_counts().sort_index()
    
        ax = df_stats.plot.bar(
            legend=False,
            figsize=(15, 10),
            title='Messages per hour',
            rot=0,
            )
        ax.set_ylabel('Count')
        ax.set_xlabel('\nHour')

if __name__ == "__main__":
    fb_analyzer = FbAnalyzer('message_1.json')
    data_dict = fb_analyzer.data_dict
    df = fb_analyzer.df
    members = fb_analyzer.members
    all_members = fb_analyzer.all_members
    statistics = fb_analyzer.get_statistics()
    member_count_words = fb_analyzer.count_words(['elo'])
    reacted_messages = fb_analyzer.get_most_reacted_messages('plan', 4)
    # fb_analyzer.plot_by_day()
    # df_monthly = fb_analyzer.get_members_stats_monthly()
    # fb_analyzer.plot_by_month_members(logaritmic=False)
    # fb_analyzer.plot_by_month_total(logaritmic=False)
    # number_of_reactions_for_members = fb_analyzer.number_of_reactions_for_members()
    # fb_analyzer.plot_messages_by_hour()