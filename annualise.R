# --- Backward Compatibility Wrappers ---

#' @export
annualise_pay <- function(data, amt, pd, outvar) {
  # Liam's original interface: returns the whole dataframe
  annualise_col(data, {{ amt }}, {{ pd }}, {{ outvar }})
}

#' @export
annualise_values <- function(values, period, def.val = -9) {
  # Luke's original interface: returns a vector
  annualise(values, period, def.val = def.val)
}

#' @export
annualise_values_deprec <- annualise_values

#' @export
ANNUALISE <- annualise_values

#' @export
monthly_values <- function(values, period, def.val = -9) {
  # Derivative of the annualise function
  res <- annualise(values, period, def.val = def.val)
  
  # Ensure we don't divide the error codes (-8, -9) by 12
  data.table::fcase(
    res < 0, res,
    default = round(res / 12, 2)
  )
}


Input Period,Annual Multiplier,Notes
"1, 90, 95",365/7,Weekly
5,12,Monthly
52,1,Already Annual
97 / ≤0,-8,Invalid/Unknown

#' Annualisation Engine (Internal)
#' @description The single source of truth for pay period multipliers.
calc_annual_multiplier <- function(period) {
  data.table::fcase(
    period %in% c(1, 90, 95), 365 / 7,
    period == 2,              365 / 14,
    period == 3,              365 / 21,
    period == 4,              365 / 28,
    period == 5,              12,
    period == 7,              6,
    period == 8,              8,
    period == 9,              9,
    period == 10,             10,
    period == 13,             4,
    period == 26,             2,
    period == 52,             1,
    default = NA_real_
  )
}

#' Annualise Values
#' @description Exposed function for direct interaction (Excel-friendly).
#' @export
annualise <- function(values, period, def.val = -9) {
  # Logic: If values are negative, keep them. 
  # If period is invalid (<=0 or 97), return -8.
  # Otherwise, multiply by period factor.
  
  multiplier <- calc_annual_multiplier(period)
  
  res <- data.table::fcase(
    values < 0,                      values,
    is.na(multiplier),               def.val,
    period <= 0 | period == 97,      -8,
    default = values * multiplier
  )
  
  return(round(res, 2))
}

#' Annualise Column
#' @description Tidy-compatible function for data frames/tables.
#' @export
annualise_col <- function(.data, amt_col, pd_col, out_col) {
  # Handles both bare names (tidy-eval) and string inputs
  .data |>
    tidytable::mutate(
      {{ out_col }} := annualise({{ amt_col }}, {{ pd_col }})
    )
}

#' Estimated Pay Bands
#' @export
estimated_pay_bands <- function(pay_amount, est_amount) {
  pay_bands <- c(0, 4999, 6999, 9999, 12999, 14999, 17999, 
                 19999, 23999, 27999, 35999, 45999, 59999, 99999997)
  
  # Logic: If annualisation failed (-8), use the estimate, 
  # otherwise find the bucket.
  data.table::fcase(
    pay_amount == -8, est_amount,
    pay_amount >= 0,  as.numeric(cut(pay_amount, breaks = pay_bands, labels = FALSE)),
    default = NA_real_
  )
}
