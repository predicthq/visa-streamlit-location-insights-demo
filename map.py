import streamlit as st
import pytz
import pandas as pd
from utils.pages import set_page_config
from utils.sidebar import show_sidebar_options, show_map_sidebar_code_examples
from utils.metrics import show_metrics
from utils.predicthq import (
    get_api_key,
    fetch_events,
    fetch_event_spend_total,
    ATTENDED_CATEGORIES,
    NON_ATTENDED_CATEGORIES,
    UNSCHEDULED_CATEGORIES,
)
from utils.map import show_map


def main():

    set_page_config("Map")
    show_sidebar_options()

    if get_api_key() is not None:
        map()
    else:
        st.warning("Please set a PredictHQ API Token.", icon="⚠️")


def map():
    location = st.session_state.location if "location" in st.session_state else None
    daterange = st.session_state.daterange if "daterange" in st.session_state else None
    if (daterange is not None):
        # Pull out date range to make them easier to work with
        date_from = daterange["date_from"]
        date_to = daterange["date_to"]

    suggested_radius = (
        st.session_state.suggested_radius
        if "suggested_radius" in st.session_state
        else None
    )
    radius = st.session_state.radius if "radius" in st.session_state else None

    if (
        location is None
        or daterange is None
        or suggested_radius is None
        or radius is None
    ):
        return
    
    # Pull out date range to make them easier to work with
    date_from = daterange["date_from"]
    date_to = daterange["date_to"]

    # Allow selecting categories
    categories = ATTENDED_CATEGORIES + NON_ATTENDED_CATEGORIES + UNSCHEDULED_CATEGORIES
    default_categories = ATTENDED_CATEGORIES
    selected_categories = st.sidebar.multiselect(
        "Event categories",
        options=categories,
        default=default_categories,
        help="[Event Categories Docs](https://docs.predicthq.com/resources/events)",
        key="categories",
    )

    total_event_spend = fetch_event_spend_total(
            location["lat"],
            location["lon"],
            radius,
            date_from=date_from,
            date_to=date_to,
            categories=selected_categories,
            tz=location["tz"],
        )

    st.title("Location : " +location["address"])
    st.header("Total Predicted Event Spend : ${:,}".format(total_event_spend["spend_total"]))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Hospitality Spend",
            value="${:,}".format(total_event_spend["spend_hospo"]),
        )
        
    with col2:
        st.metric(
            label="Accommodation Spend",
            value="${:,}".format(total_event_spend["spend_accom"]),
        )
    with col3:
        st.metric(
            label="Transportation Spend",
            value="${:,}".format(total_event_spend["spend_trans"]),
        )

    # Display metrics
    show_metrics()

    # We have a bunch of code examples in the docs/code_examples folder
    show_map_sidebar_code_examples()

    # Fetch events
    events = fetch_events(
        location["lat"],
        location["lon"],
        radius=radius,
        date_from=date_from,
        date_to=date_to,
        tz=location["tz"],
        categories=selected_categories,
        radius_unit=suggested_radius["radius_unit"],
    )

    # Show map and convert radius miles to meters (the map only supports meters)
    show_map(
        lat=location["lat"],
        lon=location["lon"],
        radius_meters=calc_meters(radius, suggested_radius["radius_unit"]),
        events=events,
    )

    show_events_list(events, f'events-{location["id"]}-{date_from}-to-{date_to}')


def calc_meters(value, unit):
    if unit == "mi":
        return value * 1609
    if unit == "ft":
        return value * 0.3048
    elif unit == "km":
        return value * 1000
    else:
        return value


def show_events_list(events, filename="events"):
    """
    We're also converting start/end times to local timezone here from UTC.
    """
    results = []

    for event in events["results"]:
        venue = next(
            filter(lambda entity: entity["type"] == "venue", event["entities"]), None
        )

        row = {
            # "id": event["id"],
            "Title": event["title"],
            "Predicted Attendance": event["phq_attendance"] if event["phq_attendance"] else 0,
            "Category": event["category"],
            "Venue": venue["name"] if venue else "",
            "Start Date": event["start"]
            .astimezone(pytz.timezone(event["timezone"])).strftime('%Y-%m-%d %H:%M:%S')
            if event["timezone"] is not None
            else event["start"].strftime('%Y-%m-%d %H:%M:%S'),
            "End Date": event["end"]
            .astimezone(pytz.timezone(event["timezone"])).strftime('%Y-%m-%d %H:%M:%S')
            if event["timezone"] is not None
            else event["end"].strftime('%Y-%m-%d %H:%M:%S'),
            "Predicted End Date": event["predicted_end"]
            .astimezone(pytz.timezone(event["timezone"])).strftime('%Y-%m-%d %H:%M:%S')
            if "predicted_end" in event
            and event["predicted_end"] is not None
            and event["timezone"] is not None
            else "",
            "Hospitality Spend": "${:,}".format(event["predicted_event_spend_industries"]["hospitality"])
            if "predicted_event_spend_industries"  in event
            and event["predicted_event_spend_industries"] is not None
            else "",
            "Accommodation Spend": "${:,}".format(event["predicted_event_spend_industries"]["accommodation"])
            if "predicted_event_spend_industries"  in event
            and event["predicted_event_spend_industries"] is not None
            else "",
            "Transportation Spend": "${:,}".format(event["predicted_event_spend_industries"]["transportation"])
            if "predicted_event_spend_industries"  in event
            and event["predicted_event_spend_industries"] is not None
            else "",            
            # "venue_address": venue["formatted_address"] if venue else "",
            "placekey": event["geo"]["placekey"]
            if "geo" in event and "placekey" in event["geo"]
            else "",
        }

        results.append(row)

    events_df = pd.DataFrame(results)
    st.dataframe(events_df)

    @st.cache_data
    def convert_df(df):
        return df.to_csv().encode("utf-8")

    csv = convert_df(events_df)

    st.download_button(
        label="✅ Download events as CSV",
        data=csv,
        file_name=f"{filename}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
