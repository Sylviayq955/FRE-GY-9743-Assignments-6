"""Convention-driven factory adapted from the instructor template.

Swap axis1 is tenor or start-offset x tenor. FRA uses start-offset x end-offset,
with both offsets measured from value_date, or two explicit ISO dates.
"""

from typing import Any
from fixedincomelib.date import Date, Period, TermOrDate, add_period
from fixedincomelib.market.data_conventions import (
    CompoundingMethod, DataConvention, DataConventionFRA,
    DataConventionRFRSwap, DataConventionOvernightIndexBasisSwap,
)
from fixedincomelib.product.product_interfaces import ProductBuilderRegistry
from fixedincomelib.product.linear_products import ProductFRA, ProductRFRSwap, ProductOvernightIndexBasisSwap
from fixedincomelib.product.utilities import PayOrReceive


class ProductFactory:
    @classmethod
    def create_product_from_data_convention(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConvention,
        values: float,
        **kwargs: Any,
    ):

        convention_obj: DataConvention = data_convention
        prod_type = convention_obj.type()
        func = ProductBuilderRegistry().get(prod_type)
        return func(value_date, axis1, convention_obj, values, **kwargs)

    @classmethod
    def create_rfr_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionRFRSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductRFRSwap:

        #TODO
        effective_date, term_or_termination_date = cls._swap_dates(value_date, axis1, data_convention)
        return ProductRFRSwap(
            effective_date=effective_date,
            term_or_termination_date=term_or_termination_date,
            payment_off_set=data_convention.payment_offset,
            on_index=data_convention.index_str,
            fixed_rate=values,
            pay_or_rec=PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            notional=kwargs.get("notional", 1e4),
            accrual_period=data_convention.acc_period,
            accrual_basis=data_convention.acc_basis,
            floating_leg_accrual_period=kwargs.get("floating_leg_accrual_period", data_convention.acc_period),
            pay_business_day_convention=data_convention.business_day_convention,
            pay_holiday_convention=data_convention.holiday_convention,
            spread=kwargs.get("spread", 0.0),
            compounding_method=data_convention.compounding_method,
        )

    @classmethod
    def create_overnight_index_basis_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionOvernightIndexBasisSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductOvernightIndexBasisSwap:

        #TODO
        effective_date, term_or_termination_date = cls._swap_dates(value_date, axis1, data_convention)
        return ProductOvernightIndexBasisSwap(
            effective_date=effective_date,
            term_or_termination_date=term_or_termination_date,
            payment_off_set=data_convention.payment_offset,
            on_index_1=data_convention.index_1_str,
            on_index_2=data_convention.index_2_str,
            spread_over_leg_1=values,
            pay_or_rec_leg_1=PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            notional=kwargs.get("notional", 1e4),
            accrual_period_1=data_convention.acc_period_1,
            accrual_basis=data_convention.acc_basis,
            accrual_period_2=data_convention.acc_period_2,
            pay_business_day_convention=data_convention.business_day_convention,
            pay_holiday_convention=data_convention.holiday_convention,
            compounding_method=data_convention.compounding_method,
        )

    @classmethod
    def _swap_dates(cls, value_date, axis1, data_convention):
        """Swap date rule: 'TENOR' spot-starting; 'START x TENOR' forward-starting;
        'ISO x ISO' explicit start and end."""
        first, second = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention
        if second is None:
            # "1Y": spot-starting, run for the tenor.
            effective_date = add_period(value_date, Period("0D"), bdc, holidays)
            return effective_date, first
        if first.is_term():
            # "3Mx1Y": start in 3 months, then run for 1 year.
            effective_date = add_period(value_date, first.get_term(), bdc, holidays)
        else:
            # "2026-04-02x2027-04-02": explicit start and end dates.
            effective_date = first.get_date()
        return effective_date, second

    @classmethod
    def create_fra(cls, value_date, axis1, data_convention, values, **kwargs):
        start, end = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention
        if start.is_term():
            effective_date = add_period(value_date, start.get_term(), bdc, holidays)
            termination_date = add_period(value_date, end.get_term(), bdc, holidays)
        else:
            effective_date = start.get_date()
            termination_date = end.get_date()
        return ProductFRA(
            effective_date, TermOrDate(termination_date), data_convention.index_str,
            values, PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            kwargs.get("notional", 1e4), data_convention.acc_basis, bdc, holidays,
        )

    @staticmethod
    def _tokenize_axis1(axis1):
        tokens = axis1.strip().replace("X", "x").split("x")
        first = TermOrDate(tokens[0].strip())
        second = TermOrDate(tokens[1].strip()) if len(tokens) == 2 else None
        return first, second


ProductBuilderRegistry().register(DataConventionFRA.type(), ProductFactory.create_fra)
ProductBuilderRegistry().register(DataConventionRFRSwap.type(), ProductFactory.create_rfr_swap)
ProductBuilderRegistry().register(DataConventionOvernightIndexBasisSwap.type(),
                                  ProductFactory.create_overnight_index_basis_swap)
