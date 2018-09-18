# Calling libraries

library(foreign)
library(forecast)
library(zoo)
library(PerformanceAnalytics)

# Import data and convert to time series

data <- read.csv('../data/interim/grouped.csv')

data.ts <- ts(data, freq=365.25/7, start=2016+(5*31)/365.25)

# function to perform auto-arima on local serivces data
auto <- function(series){
  
  bestfit <- list(aicc=Inf)
  for(i in 1:25)
  {
    fit <- auto.arima(series, xreg=fourier(series, K=i), seasonal=TRUE)
    if(fit$aicc < bestfit$aicc)
      bestfit <- fit
    else break;
  }
  fc <- forecast(bestfit, xreg=fourier(series, K=1, h=12))
  return(c(series, fc$mean))
}

# forecast local services requests
forecasts <- lapply(data.ts[, -c(1:2)], auto)

forecasts.weeks <- cbind(rep(2018, 12), seq(from = 36, to = 47)) 

colnames(forecasts.weeks) <- colnames(data[, c(1:2)]) 

series.times <- rbind(data[, c(1:2)], forecasts.weeks)

output <- cbind(series.times, data.frame(forecasts))

# save forecasts
write.csv(output, '../data/processed/services_count_forecasts.csv')

