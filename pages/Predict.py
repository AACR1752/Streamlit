import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
import modules as md
import plotly.graph_objects as go
import pydeck as pdk


st.title("Predict House Prices")

if "trained_model" in st.session_state:
    model = st.session_state["trained_model"]

    # Convert back to DataFrame
    X_test = pd.DataFrame(st.session_state["X_test_values"], 
                          columns=st.session_state["X_test_columns"], 
                          index=st.session_state["X_test_index"])
    
    joined_df = pd.DataFrame(st.session_state["joined_df_values"], 
                             columns=st.session_state["joined_df_columns"], 
                             index=st.session_state["joined_df_index"])
    
    y_test = pd.Series(st.session_state["y_test"], name="Price")  # Restores index
    model_choice = st.session_state["model_choice"]

    # TODO: Bring in the filters for neighbourhood, property_type, bedrooms, bathrooms
    
    # st.selectboxes 
    neighbourhood_name = st.selectbox("Select Neighourhood", joined_df['neighbourhood'].unique().tolist())
    # bedroom_selection = st.selectbox("Select Bedroom", joined_df['bedrooms'].tolist())
    # bathroom_selection = st.selectbox("Select Bathroom", joined_df['bathrooms'].tolist())
    small_df = joined_df[(joined_df['neighbourhood'] == neighbourhood_name)]
    property_type_selection = st.selectbox("Select Property Type", small_df['property_type'].unique().tolist())

    # TODO: joined_df will shrink based on the selection above
    filtered_df = joined_df[
    (joined_df['neighbourhood'] == neighbourhood_name) &
    # (joined_df['bedrooms'] == bedroom_selection) &
    # (joined_df['bathrooms'] == bathroom_selection) &
    (joined_df['property_type'] == property_type_selection)]

    # Dropdown to select a value from X_test
    # Update the selectbox for the house listing based on the filtered DataFrame
    try: 
        datapoint = st.selectbox("Select House", filtered_df['listing'].tolist())

        # Get the index of the selected house
        index = filtered_df[filtered_df['listing'] == datapoint].index.tolist()
        single_data_point = X_test.iloc[[index[0]]]

        school_df = pd.read_csv('data/good_data/schools.csv')

        # Define House Layer (Blue Circles)
        house_layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered_df,
            get_position=["longitude", "latitude"],
            get_radius=50,  # Adjust size
            get_fill_color=[0, 0, 255, 180],  # Blue for houses
            pickable=True,
            opacity=0.8,
        )

        # Define School Layer (Red Triangles)
        school_layer = pdk.Layer(
            "ScatterplotLayer",
            data=school_df,
            get_position=["longitude", "latitude"],
            get_radius=80,  # Bigger size for schools
            get_fill_color=[255, 0, 0, 200],  # Red for schools
            pickable=True,
            opacity=0.9,
        )

        # Set the Map View
        view_state = pdk.ViewState(
            latitude=filtered_df["latitude"].mean(),
            longitude=filtered_df["longitude"].mean(),
            zoom=13,  # Adjust zoom for visibility
            pitch=30,  # Adds slight tilt for better visualization
        )

        # Display the Map with Mapbox Style (Hybrid with Amenities)
        st.pydeck_chart(pdk.Deck(
            layers=[house_layer, school_layer],
            initial_view_state=view_state,
            tooltip={"text": "{listing}\n{school_name}"},
            map_style="mapbox://styles/mapbox/satellite-streets-v12"  # Hybrid map with schools/amenities
            # map_style="pdk.map_styles.ROAD"
        ))

        # st.map(filtered_df[["latitude", "longitude"]])

    except:
        st.write("There is no available listings with current selection!")

    if st.button("Predict"):
        # Celebration Effect (Optional)
        # st.balloons()  # Adds a fun animation effect!

        prediction = model.predict(single_data_point)
        st.subheader("Single Data Point Prediction")

        st.image(joined_df.loc[index[0], 'image-src'])

        # st.write(f"image url {joined_df.loc[index[0], 'image-src']}")

        final_output = [[round(prediction[0]), round(y_test.iloc[index[0]])]]
        single_point_df = pd.DataFrame(final_output, columns=['Predicted Price','Actual Price'])

        st.dataframe(single_point_df)


        # Predicted Range
        rmse = int(round(st.session_state["rmse"],0))
        predicted_price = final_output[0][0]
        min_price = predicted_price - rmse  
        max_price = predicted_price + rmse

        # Normalize the predicted price for plotting
        normalized_price = (predicted_price - min_price) / (max_price - min_price)

        # Create figure
        fig = go.Figure()

        # Add background price range bar (Fix width)
        fig.add_trace(go.Bar(
            x=[min_price, max_price],  # Correctly setting x values
            y=[1, 1],  # Keep y the same for horizontal alignment
            orientation="h",
            marker=dict(
                color=["#4285F4", "#34A853", "#EA4335"],  # Gradient color from blue to red
            ),
            width=0.2,  # Make the bar thick enough to be visible
            showlegend=False
        ))

        # Layout adjustments
        fig.update_layout(
            # title="Predicted Price Indicator",
            xaxis=dict(
                title="Price Range",
                range=[min_price - 100000, max_price + 100000],  # Extend range slightly
                tickvals=[min_price, predicted_price, max_price],
                ticktext=[f"${min_price:,}", f"${predicted_price:,}", f"${max_price:,}"],
                tickfont=dict(
                    size=14,  # Increase font size
                    color="black",  # Change font color if needed
                    family="Arial, sans-serif"  # Change font family if needed
        ),
            ),
            yaxis=dict(visible=False),
            width=700,
            height=150,
            plot_bgcolor="rgba(0,0,0,0)",
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)

        # log_distance_to_nearest_school
        # Rename the column in X_test
        X_test = X_test.rename(columns={'log_distance_to_nearest_school': 'Proximity to School'})
        # Define the suffixes to remove
        suffixes_to_remove = ['driveway_parking', 'frontage_type',
                            'basement_type', 'lot_features', 'exterior_feature',
                            'waterfront_features', 'appliances_included']

        # Rename columns in X_test
        X_test.columns = [md.remove_suffixes(col, suffixes_to_remove) for col in X_test.columns]
        colors = ["gold", "silver", "#cd7f32", "#DAA520", "#B22222"]
        badge = ["🥇", "🥈", "🥉", "🏅", "🎖️"]
    
        # Maintain the order of columns
        column_order = X_test.columns.tolist()

        if model_choice == "Ridge Regression":
            feature_importance = model.coef_
            single_data_point_array = single_data_point.values
            output = np.multiply(feature_importance , single_data_point_array) # this is for linear regression

            absolute_coefficients_y = np.abs(output[0])
            percentages_y = (absolute_coefficients_y / np.sum(absolute_coefficients_y)) * 100

            # Combine feature names and percentages, then sort by percentages in descending order
            sorted_features = sorted(zip(column_order, percentages_y), key=lambda x: x[1], reverse=True)
        elif model_choice == "Random Forest":
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(single_data_point)

            # Calculate absolute SHAP values and convert to percentages
            absolute_shap_values = np.abs(shap_values[0]) # Extract SHAP values for this instance
            percentages = (absolute_shap_values / np.sum(absolute_shap_values)) * 100
  
            # Sort features by percentage contribution in descending order
            sorted_features = sorted(list(zip(column_order, percentages)), key=lambda x: x[1], reverse=True)

        # List of words to drop columns containing them
        words_to_drop = md.words_to_drop

        # Filter sorted_features to remove any feature names containing the words in words_to_drop
        filtered_sorted_features = [feature for feature in sorted_features if not md.should_drop(feature[0], words_to_drop)]

        # Select the top 20 features
        top_features_y = filtered_sorted_features[:20]
        top_feature_names_y, top_percentages_y = zip(*top_features_y)

        top_feature_names_y = [name.replace('_', ' ') for name in top_feature_names_y]

        # Convert tuple to list and extract strings
        top_names = [str(name) for name in top_feature_names_y]
        top_scores = [float(score) for score in top_percentages_y]

        # Title
        st.title("🏆 Top 5 features")

        for i in range(0,5):
            # 1st Place
            with st.container():
                st.markdown(
                    f"""
                    <div style="text-align: center; padding: 20px; border-radius: 10px; background-color: {colors[i]};">
                        <h2>{badge[i]} {top_names[i]}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            
                st.markdown("<br>", unsafe_allow_html=True)
        
        md.display_graph(top_feature_names=top_feature_names_y,
                         top_percentages=top_percentages_y)

else:
    st.error("No trained model or test data found! Please train the model first.")