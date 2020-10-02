import graphene

from ....core.permissions import ProductPermissions
from ....graphql.core.types import Money, MoneyRange
from ....product import models
from ....product.utils.costs import get_margin_for_variant, get_product_costs_data
from ...channel.dataloaders import (
    ChannelByProductChannelListingIDLoader,
    ChannelByProductVariantChannelListingIDLoader,
)
from ...core.connection import CountableDjangoObjectType
from ...decorators import permission_required


class Margin(graphene.ObjectType):
    start = graphene.Int()
    stop = graphene.Int()


class ProductChannelListing(CountableDjangoObjectType):
    discounted_price = graphene.Field(
        Money, description="The price of the cheapest variant (including discounts)."
    )
    purchase_cost = graphene.Field(MoneyRange, description="Purchase cost of product.")
    margin = graphene.Field(Margin, description="Gross margin percentage value.")

    class Meta:
        description = "Represents product channel listing."
        model = models.ProductChannelListing
        interfaces = [graphene.relay.Node]
        only_fields = ["id", "channel", "is_published", "publication_date"]

    @staticmethod
    def resolve_channel(root: models.ProductChannelListing, info, **_kwargs):
        return ChannelByProductChannelListingIDLoader(info.context).load(root.id)

    @staticmethod
    @permission_required(ProductPermissions.MANAGE_PRODUCTS)
    def resolve_purchase_cost(root: models.ProductChannelListing, *_args):
        # TODO: Add dataloader.
        variants = root.product.variants.all().values_list("id", flat=True)
        channel_listings = models.ProductVariantChannelListing.objects.filter(
            variant_id__in=variants, channel_id=root.channel_id
        )
        purchase_cost, _ = get_product_costs_data(root, channel_listings)
        return purchase_cost

    @staticmethod
    @permission_required(ProductPermissions.MANAGE_PRODUCTS)
    def resolve_margin(root: models.ProductChannelListing, *_args):
        # TODO: Add dataloader.
        variants = root.product.variants.all().values_list("id", flat=True)
        channel_listings = models.ProductVariantChannelListing.objects.filter(
            variant_id__in=variants, channel_id=root.channel_id
        )
        _, margin = get_product_costs_data(root, channel_listings)
        return Margin(margin[0], margin[1])


class ProductVariantChannelListing(CountableDjangoObjectType):
    cost_price = graphene.Field(Money, description="Cost price of the variant.")
    margin = graphene.Int(description="Gross margin percentage value.")

    class Meta:
        description = "Represents product varaint channel listing."
        model = models.ProductVariantChannelListing
        interfaces = [graphene.relay.Node]
        only_fields = ["id", "channel", "price", "cost_price"]

    @staticmethod
    def resolve_channel(root: models.ProductVariantChannelListing, info, **_kwargs):
        return ChannelByProductVariantChannelListingIDLoader(info.context).load(root.id)

    @staticmethod
    @permission_required(ProductPermissions.MANAGE_PRODUCTS)
    def resolve_margin(root: models.ProductVariantChannelListing, *_args):
        variant_channel_listing = root.objects.filter(
            channel_id=root.channel_id
        ).first()
        if not variant_channel_listing:
            return None
        return get_margin_for_variant(variant_channel_listing)
