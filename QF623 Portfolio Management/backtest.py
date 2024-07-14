import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
from matplotlib import patheffects
from performance import performance

class backtest:
    def __init__(
            self,
            start_date: str,
            end_date: str,
            rebal_freq: str,
            spot: pd.DataFrame,
            spot_ret: pd.DataFrame,
            benchmark_ret: pd.DataFrame,
            weights: dict[str, list[float]],
            benchmark_weights: dict[str, list[float]],
            slippage: float,
            leverage: int,
            max_short_weight: float,
            downside_risk: float,
            metrics: list,
            charts: bool
        ) -> None:
        '''
        rebal_freq: 'MS' = Month Start, 'QS' = Quarter Start
        weights = {
            '2024-01-01' : [0.1, 0.1, 0.1...], 
            '2024-04-01' : [0.1, 0.1, 0.1...]
                   }
        '''
        self.rebal_freq = rebal_freq
        if rebal_freq != 'dynamic':
            self.rebal_dates = pd.date_range(start_date, pd.to_datetime(end_date) + pd.offsets.MonthBegin(0), freq = rebal_freq, inclusive = 'left').strftime('%Y-%m-%d').tolist()
        else:
            self.rebal_dates = self.weights.key().tolist()

        self.timeframe = [1, 5] # in years
        self.weights = weights

        self.spot = spot
        self.spot_ret = spot_ret

        self.benchmark_ret = benchmark_ret
        self.benchmark_weights = benchmark_weights

        self.risk_free = spot_ret['RF']
        self.slippage = -slippage 
        self.leverage = leverage
        self.max_short_weight = max_short_weight
        self.downside_risk = downside_risk  
        self.metrics = metrics
        self.master = pd.DataFrame()

        self.charts = charts
        
    def rebalancing(self) -> pd.DataFrame:
        '''
        Compute Rebalancing Portfolio and Benchmark
        '''
        ###############
        ## Portfolio ##
        ###############
        for date in range(len(self.rebal_dates)):
            rebal_date = self.rebal_dates[date]
            rebal_weights = self.weights[rebal_date]
            
            # set up returns for the rebal interval
            if date + 1 != len(self.rebal_dates): # if no next rebal date, set the end period to max date of spot_ret
                if self.rebal_freq == 'MS':
                    end_period = (pd.to_datetime(rebal_date) + pd.offsets.MonthEnd(0))
                    end_period = end_period.strftime('%Y-%m-%d')
                elif self.rebal_freq == 'QS':
                    end_period = (pd.to_datetime(rebal_date) + pd.offsets.QuarterEnd(0))
                    end_period = end_period.strftime('%Y-%m-%d')
                else:
                    # dynamic rebalancing
                    end_period = self.rebal_dates[date + 1]
            else:
                end_period = self.spot_ret.index.max()

            hist_df = self.spot_ret[(self.spot_ret.index <= end_period) & (self.spot_ret.index >= rebal_date)] # filter for the period
            ret_df = hist_df.copy()
            daily_ret = hist_df.values

            # Compute daily portfolio returns
            daily_port_ret = np.zeros(len(hist_df))

            # return on rebalancing day (considering slippage)
            daily_port_ret[0] = (daily_ret[0] * rebal_weights).sum() + self.slippage

            # change in daily weight
            float_weight = rebal_weights * (1 + daily_ret[0])
            
            # Ensure total weight sum to 1 
            rebase_weight = float_weight / float_weight.sum()

            # compute portfolio returns daily based on float weight and rebased weights
            for day in range(1, len(hist_df)):
                daily_port_ret[day] = (daily_ret[day] * rebase_weight).sum()
                float_weight = rebase_weight * (1 + daily_ret[day])
                
                rebase_weight = float_weight / float_weight.sum()

            ret_df['portfolio_ret'] = daily_port_ret
            
            # append to master df
            self.master = pd.concat([self.master, ret_df[['portfolio_ret']]], axis = 0)
        
        ###############
        ## Benchmark ##
        ###############
        min_date = self.master.index.min()
        max_date = self.master.index.max()
        benchmark = self.benchmark_ret[(self.benchmark_ret.index <= max_date) & (self.benchmark_ret.index >= min_date)]

        # compute benchmark returns
        self.master['benchmark_ret'] = (benchmark * self.benchmark_weights).sum(axis = 1)
        self.master = self.master.reset_index()

        self.risk_free = self.risk_free[self.risk_free.index >= min_date].values

        return self.master

    def generate_performance(self):
        '''
        Computes performance metrics for portfolio and benchmark
        '''
       
        compute_port_perf = performance(self.master['portfolio_ret'], self.risk_free, 0)
        compute_benchmark_perf = performance(self.master['benchmark_ret'], self.risk_free, 0)
        
        self.master['portfolio_cum_ret'] = compute_port_perf.compute_cum_rets()
        self.master['benchmark_cum_ret'] = compute_benchmark_perf.compute_cum_rets()

        self.master['portfolio_drawdown'] = compute_port_perf.compute_drawdown()
        self.master['benchmark_drawdown'] = compute_benchmark_perf.compute_drawdown()
        
        for tf in self.timeframe:
            if len(self.master) > tf:
                compute_port_perf = performance(self.master['portfolio_ret'], self.risk_free, tf)
                compute_benchmark_perf = performance(self.master['benchmark_ret'], self.risk_free, tf)
                
                # Sharpe
                self.master[f'portfolio_{tf}Y_annualized_sharpe'] = compute_port_perf.compute_rolling_sharpe()
                self.master[f'benchmark_{tf}Y_annualized_sharpe'] = compute_benchmark_perf.compute_rolling_sharpe()

                # Information Ratio
                self.master[f'portfolio_{tf}Y_annualized_information_ratio'] = compute_port_perf.compute_rolling_information_ratio(self.master['benchmark_ret'])

                # Beta
                self.master[f'portfolio_{tf}Y_beta'] = compute_port_perf.compute_rolling_beta(self.master['benchmark_ret'])
                self.master[f'benchmark_{tf}Y_beta'] = compute_benchmark_perf.compute_rolling_beta(self.master['benchmark_ret'])

                # Sortino
                self.master[f'portfolio_{tf}Y_annualized_sortino'] = compute_port_perf.compute_rolling_sortino(self.downside_risk)
                self.master[f'benchmark_{tf}Y_annualized_sortino'] = compute_benchmark_perf.compute_rolling_sortino(self.downside_risk)

                # Volatility
                self.master[f'portfolio_{tf}Y_annualized_volatility'] = compute_port_perf.compute_rolling_volatility()
                self.master[f'benchmark_{tf}Y_annualized_volatility'] = compute_benchmark_perf.compute_rolling_volatility()


        return True
    
    def generate_report(self) -> None:
        '''
        1. Rebalancing Weights by Frequency
        2. Prints Trailing N years performance metrics
        3. Plots Trailing N years charts
        '''
        ###################
        ## Rebal Weights ##
        ################### 
        # weights_df = pd.DataFrame.from_dict(self.weights).T
        # weights_df.columns = self.spot_ret.columns
        # weights_df['total'] = weights_df.sum(axis = 1)
        
        # display(
        #     weights_df.style.background_gradient(cmap='RdYlGn', axis=1) \
        #                 .format("{:.1%}") \
        #                     .set_properties(**{'text-align': 'center'})
        #                 ) 

        #############
        ## Metrics ##
        #############   
        print('--------------BACKTEST REPORT--------------')
        for metric in self.metrics:
            for tf in self.timeframe:
                if len(self.master) > tf:
                    compute_port_perf = performance(self.master['portfolio_ret'].values, self.risk_free, tf)
                    compute_benchmark_perf = performance(self.master['benchmark_ret'].values, self.risk_free, tf)

                    port_cum_ret = compute_port_perf.compute_annualized_rets()
                    port_rolling_sharpe = np.nanmean(compute_port_perf.compute_rolling_sharpe())
                    port_rolling_IR = np.nanmean(compute_port_perf.compute_rolling_information_ratio(self.master["benchmark_ret"]))
                    port_rolling_sortino = np.nanmean(compute_port_perf.compute_rolling_sortino(self.downside_risk))
                    port_maxdd = compute_port_perf.compute_max_dd()
                    port_rolling_vol = np.nanmean(compute_port_perf.compute_rolling_volatility())

                    benchmark_cum_ret = compute_benchmark_perf.compute_annualized_rets()
                    benchmark_rolling_sharpe = np.nanmean(compute_benchmark_perf.compute_rolling_sharpe())
                    benchmark_rolling_sortino = np.nanmean(compute_benchmark_perf.compute_rolling_sortino(self.downside_risk))
                    benchmark_maxdd = compute_benchmark_perf.compute_max_dd()
                    benchmark_rolling_vol = np.nanmean(compute_benchmark_perf.compute_rolling_volatility())

                    print(f'T{tf}Y {metric}: {port_cum_ret}% vs {benchmark_cum_ret}% benchmark') if metric == 'Annualized Return' else \
                    print(f'T{tf}Y Average Annualized {metric}: {round(port_rolling_sharpe, 2)} vs {round(benchmark_rolling_sharpe, 2)} benchmark') if metric == 'Sharpe Ratio' else \
                    print(f'T{tf}Y Average Annualized {metric}: {round(port_rolling_IR, 2)}') if metric == 'Information Ratio' else \
                    print(f'T{tf}Y Average Annualized {metric}: {round(port_rolling_sortino, 2)} vs {round(benchmark_rolling_sortino, 2)} benchmark') if metric == 'Sortino Ratio' else \
                    print(f'T{tf}Y {metric}: {port_maxdd}% vs {benchmark_maxdd}% benchmark') if metric == 'Max Drawdown' else \
                    print(f'T{tf}Y Average Annualized {metric}: {round(port_rolling_vol, 2)}% vs {round(benchmark_rolling_vol, 2)}% benchmark') if metric == 'Volatility' else print('')
            print('###############################################')

        ############
        ## Plots ##
        ############
        if self.charts:
            to_plot = []
            for tf in self.timeframe:
                if any([i for i in self.master.columns.tolist() if str(tf) in i]):
                    to_plot.append(tf)
            
            n_rows = 3

            fig, main = plt.subplots(1, 2, figsize = (30,5), tight_layout = True)
            self.plotting_metrics(main, 0, 'cum_ret', 'Cumulative Returns (Log Scaled)')
            self.plotting_metrics(main, 1, 'drawdown', 'Drawdown')

            fig2, axs = plt.subplots(n_rows, 2, sharex = False, figsize = (30,10), tight_layout = True)
            axs = axs.flatten()
            for tf in range(len(to_plot)):
                self.plotting_metrics(axs, tf, f'{to_plot[tf]}Y_annualized_sharpe', f'{to_plot[tf]}Y Rolling Sharpe')
                self.plotting_metrics(axs, tf + 2, f'{to_plot[tf]}Y_beta', f'{to_plot[tf]}Y Rolling Beta')
                self.plotting_metrics(axs, tf + 4, f'{to_plot[tf]}Y_annualized_sortino', f'{to_plot[tf]}Y Rolling Sortino')
                
        print('--------------END------------------')

        return True
    
    def plotting_metrics(
            self, 
            ax: np.array, 
            i: int, 
            y: np.array, 
            title: str
        ) -> None:
        
        x = self.master['Date']
        y_port = self.master[f'portfolio_{y}'] if y != 'cum_ret' else np.log(self.master[f'portfolio_{y}'])
        y_benchmark = self.master[f'benchmark_{y}'] if y != 'cum_ret' else np.log(self.master[f'benchmark_{y}'])
        ax[i].plot(x, y_port, label = 'portfolio', color = 'b')
        ax[i].plot(x, y_benchmark, label = 'benchmark', color = 'k')
        ax[i].set_title(title)
        ax[i].axhline(0 if y != 'cum_ret' else 1, color = 'r', alpha = 0.2, linestyle = 'dashed')
        self.plot_crash(ax, i)
        ax[i].legend(fontsize = 'small');

        return True
    
    def plot_crash(
            self, 
            ax: np.array, 
            i: int
        ) -> None:

        financial_regimes = [
            (pd.to_datetime('1991-01-01'), pd.to_datetime('2004-01-01'), '1990-2000 Dot-com Bubble'),
            (pd.to_datetime('2007-06-01'), pd.to_datetime('2008-12-31'), '2008 GFC'),
            (pd.to_datetime('2010-05-01'), pd.to_datetime('2012-07-01'), '2010-2012 Euro Debt Crisis'),
            (pd.to_datetime('2015-07-01'), pd.to_datetime('2015-12-31'), '2015 Chinese Stock Market Crash'),
            (pd.to_datetime('2018-10-01'), pd.to_datetime('2018-12-24'), '2018 US-China Trade War'),
            (pd.to_datetime('2020-02-19'), pd.to_datetime('2020-03-23'), '2020 COVID-19'),
            (pd.to_datetime('2021-11-14'), pd.to_datetime('2022-12-25'), '2022 I/R Hike & Russia-Ukraine War')
        ]
        # Add shaded areas to indicate financial crisis boundaries
        label_offset = 0  # initial offset for label placement
        for crisis in financial_regimes:
            start_date, end_date, crisis_label = crisis
            ax[i].axvspan(start_date, end_date, color='red', alpha=0.3)
            # Calculate midpoint of the crisis period
            crisis_midpoint = start_date + (end_date - start_date) / 2
            # Shift label down by a certain offset
            effect = [patheffects.withStroke(linewidth=3, foreground='white')]  # Adding grey outline
            ax[i].text(crisis_midpoint, ax[i].get_ylim()[1]*0.9 - label_offset, crisis_label, verticalalignment='top', horizontalalignment='center', path_effects=effect)

            offset = ax[i].get_ylim()[1] / 8 if int(ax[i].get_ylim()[1]) != 0.0 else -ax[i].get_ylim()[0] / 8
            label_offset += offset  # increase offset for the next label
    
    def run(self):
        self.rebalancing()
        self.generate_performance()
        self.generate_report()
        return True